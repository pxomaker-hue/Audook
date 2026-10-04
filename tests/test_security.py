"""Hardening of /api/cast/local-audio (no open proxy, no arbitrary file
read) and /api/shutdown (localhost only)."""
from pathlib import Path

import pytest

from app import DATA_DIR


def get_audio(client, path):
    return client.get("/api/cast/local-audio", query_string={"path": str(path)})


def test_missing_path_is_404(client, db):
    assert get_audio(client, "").status_code == 404


def test_remote_url_to_unknown_host_is_refused(client, db):
    assert get_audio(client, "http://169.254.169.254/latest/x.mp3").status_code == 403


def test_local_file_outside_library_roots_is_refused(client, db, tmp_path):
    outside = tmp_path / "secret.mp3"
    outside.write_bytes(b"ID3")
    assert get_audio(client, outside).status_code == 403


def test_non_audio_extension_is_not_served(client, db, tmp_path):
    (tmp_path / "notes.txt").write_text("hi")
    assert get_audio(client, tmp_path / "notes.txt").status_code == 404


def test_file_inside_a_local_library_folder_is_served(client, seed_book, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    track = library / "chapter.mp3"
    track.write_bytes(b"ID3" + b"\0" * 64)
    seed_book(server_type="local", url=str(library))
    response = get_audio(client, track)
    assert response.status_code == 200
    assert response.data.startswith(b"ID3")


def test_path_traversal_out_of_library_is_refused(client, seed_book, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    secret = tmp_path / "secret.mp3"
    secret.write_bytes(b"ID3")
    seed_book(server_type="local", url=str(library))
    assert get_audio(client, library / ".." / "secret.mp3").status_code == 403


def test_file_in_audook_data_dir_is_served(client, db):
    track = DATA_DIR / "cache" / "cleaned_test.mp3"
    track.write_bytes(b"ID3")
    try:
        assert get_audio(client, track).status_code == 200
    finally:
        track.unlink()


class _FakeUpstream:
    status_code = 206
    headers = {"Content-Type": "audio/mpeg", "Content-Range": "bytes 0-2/10", "Transfer-Encoding": "chunked"}

    def iter_content(self, chunk_size=8192):
        yield b"abc"


def test_remote_url_on_a_configured_server_is_proxied_without_redirects(client, seed_book, monkeypatch):
    seed_book(server_type="audiobookshelf", url="http://nas.local:13378")
    calls = {}

    def fake_get(url, **kwargs):
        calls.update(kwargs, url=url)
        return _FakeUpstream()

    monkeypatch.setattr("app.api.cast.requests.get", fake_get)
    response = client.get("/api/cast/local-audio", headers={"Range": "bytes=0-2"},
                          query_string={"path": "http://nas.local:13378/s/item/x.mp3"})
    assert response.status_code == 206
    assert response.data == b"abc"
    assert calls["allow_redirects"] is False
    assert calls["headers"]["Range"] == "bytes=0-2"
    assert "Transfer-Encoding" not in response.headers


def test_shutdown_is_localhost_only(client, db):
    assert client.post("/api/shutdown", environ_base={"REMOTE_ADDR": "192.168.1.50"}).status_code == 403
    assert client.post("/api/shutdown", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 200
