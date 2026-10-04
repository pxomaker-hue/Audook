"""Pure-logic unit tests: tag cleaning, cast content types, chapter titles
and the sleep timer's fade/cancel semantics (which the Android plugin
re-implements in Kotlin - AudookPlayerPlugin.kt)."""
import pytest

from app.api.helpers import format_chapter_title
from app.cast.cast_player import CastPlayer
from app.local.scanner import _clean_tag, _is_usable_albumartist, _primary_name
import importlib

ps = importlib.import_module("app.services.player_service")  # the module (app.services re-exports an instance under the same name)
PlayerService = ps.PlayerService


# ---------- chapter titles ----------

def test_format_chapter_title_is_one_based():
    assert format_chapter_title(0, "Intro") == "1. Intro"
    assert format_chapter_title(9, "Fin") == "10. Fin"
    assert format_chapter_title(0, None) is None


# ---------- local scanner tag helpers ----------

@pytest.mark.parametrize("raw,expected", [
    ("J_K_Rowling", "J K Rowling"),
    ("Isaac__Asimov", "Isaac Asimov"),
    ("Normal Name", "Normal Name"),
    ("___", None),
    (None, None),
])
def test_clean_tag(raw, expected):
    assert _clean_tag(raw) == expected


def test_primary_name_drops_translator_credits():
    assert _primary_name("Andrzej Sapkowski, Lydia Cantin-Waleryszak - traducteur") == "Andrzej Sapkowski"
    assert _primary_name("Solo") == "Solo"
    assert _primary_name(None) is None


@pytest.mark.parametrize("albumartist,artist,usable", [
    ("Real Author", "Narrator", True),
    ("Same", "Same", False),              # duplicate of artist
    (None, "Narrator", False),
    ("Author\tLu par :", "Author", False),  # malformed Audiolib tag (tab)
    ("Author - Lu par :", "Other", False),  # dangling "Lu par" label
])
def test_is_usable_albumartist(albumartist, artist, usable):
    assert _is_usable_albumartist(albumartist, artist) is usable


# ---------- cast content types ----------

@pytest.mark.parametrize("url,expected", [
    ("http://x/book.m4b", "audio/mp4"),
    ("http://x/book.M4A", "audio/mp4"),
    ("http://x/a.mp3?token=abc", "audio/mpeg"),
    ("C:\books\a.flac", "audio/flac"),
    ("http://x/a.opus", "audio/ogg"),
    ("http://x/unknown.bin", "audio/mpeg"),
])
def test_cast_content_type_guess(url, expected):
    assert CastPlayer._guess_content_type(url) == expected


# ---------- sleep timer ----------

@pytest.fixture()
def player(monkeypatch):
    monkeypatch.setattr(ps.time, "sleep", lambda s: None)  # no real waiting
    service = PlayerService()
    service.calls = []
    monkeypatch.setattr(service, "get_volume", lambda: 0.8)
    monkeypatch.setattr(service, "set_volume", lambda v: service.calls.append(("volume", round(v, 4))))
    monkeypatch.setattr(service, "pause", lambda: service.calls.append(("pause",)))
    return service


def test_timer_reports_remaining_time_and_cancels(player, monkeypatch):
    monkeypatch.setattr(player, "_sleep_timer_loop", lambda generation: None)  # don't run the thread body
    assert player.get_sleep_timer_remaining_seconds() is None
    player.set_sleep_timer(5)
    assert 295 < player.get_sleep_timer_remaining_seconds() <= 300
    player.cancel_sleep_timer()
    assert player.get_sleep_timer_remaining_seconds() is None


def test_zero_or_none_minutes_cancels(player, monkeypatch):
    monkeypatch.setattr(player, "_sleep_timer_loop", lambda generation: None)
    player.set_sleep_timer(10)
    player.set_sleep_timer(0)
    assert player.get_sleep_timer_remaining_seconds() is None


def test_fade_ramps_volume_to_zero_pauses_then_restores(player):
    player._sleep_timer_generation = 1
    player._fade_out_and_pause(1)
    volumes = [c[1] for c in player.calls if c[0] == "volume"]
    assert volumes[0] == 0.8                     # starts at the original volume
    assert volumes[-2] == 0.0                    # reaches silence...
    assert volumes[-1] == 0.8                    # ...then restores the original
    assert volumes[:-1] == sorted(volumes[:-1], reverse=True)  # monotonic fade
    assert ("pause",) in player.calls
    assert player.calls.index(("pause",)) == len(player.calls) - 2  # pause right before the restore


def test_fade_aborts_when_a_newer_timer_started(player):
    player._sleep_timer_generation = 1
    original_set_volume = player.set_volume

    def set_volume_then_restart(v):
        original_set_volume(v)
        player._sleep_timer_generation = 2  # user reset the timer mid-fade

    player.set_volume = set_volume_then_restart
    player._fade_out_and_pause(1)
    assert ("pause",) not in player.calls
    assert len([c for c in player.calls if c[0] == "volume"]) == 1  # stopped right after the first step
