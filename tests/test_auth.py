"""Optional API token (AUDOOK_API_TOKEN): off by default, enforced when set."""
import logging

import pytest

from app.api.auth import _RedactTokenFilter
from app.cast.cast_player import CastPlayer

TOKEN = "s3cret-token"


@pytest.fixture()
def protected(monkeypatch):
    monkeypatch.setenv("AUDOOK_API_TOKEN", TOKEN)


def test_api_is_open_when_no_token_is_configured(client, monkeypatch):
    monkeypatch.delenv("AUDOOK_API_TOKEN", raising=False)
    assert client.get("/api/books").status_code == 200


def test_blank_token_does_not_lock_the_api(client, monkeypatch):
    monkeypatch.setenv("AUDOOK_API_TOKEN", "   ")
    assert client.get("/api/books").status_code == 200


def test_requests_without_token_are_rejected(client, protected):
    for path in ("/api/books", "/api/servers", "/api/health", "/api/player/state"):
        assert client.get(path).status_code == 401, path
    assert client.post("/api/shutdown").status_code == 401


def test_wrong_token_is_rejected(client, protected):
    assert client.get("/api/books", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/api/books", headers={"X-Audook-Token": "nope"}).status_code == 401
    assert client.get("/api/books", headers={"Authorization": f"Basic {TOKEN}"}).status_code == 401


def test_bearer_and_custom_header_are_accepted(client, protected):
    assert client.get("/api/books", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
    assert client.get("/api/books", headers={"X-Audook-Token": TOKEN}).status_code == 200
    assert client.get("/api/health", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_liveness_and_preflight_stay_public(client, protected):
    assert client.get("/health").status_code == 200
    assert client.options("/api/books").status_code != 401


def test_query_token_only_works_on_the_media_endpoint(client, protected):
    # Not accepted on regular routes (it would end up in logs/history)...
    assert client.get("/api/books", query_string={"token": TOKEN}).status_code == 401
    # ...but accepted for the media URL ExoPlayer / a Chromecast fetch (here: past auth, then 404 for a missing path)
    ok = client.get("/api/cast/local-audio", query_string={"token": TOKEN, "path": ""})
    assert ok.status_code == 404
    bad = client.get("/api/cast/local-audio", query_string={"token": "nope", "path": ""})
    assert bad.status_code == 401


def test_rejected_request_does_not_start_the_services(client, protected):
    from app.api.context import services
    services.library = None
    assert client.get("/api/books").status_code == 401
    assert services.library is None


def test_token_is_redacted_from_request_logs():
    record = logging.LogRecord(
        "werkzeug", logging.INFO, __file__, 1,
        '127.0.0.1 - "GET /api/cast/local-audio?path=a.mp3&token=%s HTTP/1.1" 200 -', (TOKEN,), None,
    )
    record.msg = '127.0.0.1 - "GET /api/cast/local-audio?path=a.mp3&token=%s HTTP/1.1" 200 -' % TOKEN
    record.args = ()
    _RedactTokenFilter().filter(record)
    assert TOKEN not in record.getMessage()
    assert "token=***" in record.getMessage()


def test_desktop_cast_url_carries_the_token_only_when_configured(tmp_path, monkeypatch):
    track = tmp_path / "book.m4b"
    track.write_bytes(b"x")
    player = CastPlayer()
    monkeypatch.delenv("AUDOOK_API_TOKEN", raising=False)
    assert "token=" not in player._resolve_media_url(str(track))
    monkeypatch.setenv("AUDOOK_API_TOKEN", "a b&c")
    url = player._resolve_media_url(str(track))
    assert url.endswith("&token=a%20b%26c")
    assert "/api/cast/local-audio?path=" in url
