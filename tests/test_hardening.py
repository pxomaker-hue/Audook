"""Upstream-token redaction, SSRF guard on the cover proxy and player input validation."""
from app.api.sources import is_public_address, public_cover_url, strip_secret_params
from app.database import get_session


def test_strip_secret_params_removes_tokens_only():
    assert strip_secret_params("http://h/api/x?token=abc&a=1") == "http://h/api/x?a=1"
    assert strip_secret_params("http://h/p?X-Plex-Token=abc") == "http://h/p"
    assert strip_secret_params("http://h/p") == "http://h/p"
    assert strip_secret_params(None) is None


def test_private_and_loopback_addresses_are_not_public():
    for host in ("127.0.0.1", "10.0.0.5:8080", "169.254.169.254", "192.168.1.2", "[::1]:80"):
        assert not is_public_address(host)


def test_book_details_never_expose_upstream_tokens(client, seed_book):
    book_id = seed_book()
    session = get_session()
    from app.database.models import Book
    book = session.query(Book).filter_by(id=book_id).first()
    book.chapters = [{"title": "c", "duration": 1, "audio_file": "http://nas/api/items/1/file/2?token=SECRET"}]
    book.cover_url = "http://nas/api/items/1/cover?token=SECRET"
    session.commit()
    body = client.get(f"/api/books/{book_id}").get_data(as_text=True)
    assert "SECRET" not in body
    assert f"/api/books/{book_id}/cover-proxy" in body


def test_cover_proxy_refuses_internal_targets(client, seed_book):
    book_id = seed_book()
    session = get_session()
    from app.database.models import Book
    session.query(Book).filter_by(id=book_id).first().cover_url = "http://169.254.169.254/latest/meta-data"
    session.commit()
    assert client.get(f"/api/books/{book_id}/cover-proxy").status_code == 404


def test_patch_rejects_non_http_cover(client, seed_book):
    book_id = seed_book()
    assert client.patch(f"/api/books/{book_id}", json={"cover_url": "file:///etc/passwd"}).status_code == 400


def test_player_rejects_invalid_numbers(client):
    assert client.post("/api/player/volume", json={"volume": 500}).status_code == 400
    assert client.post("/api/player/speed", json={"speed": "fast"}).status_code == 400
    assert client.post("/api/player/seek", json={}).status_code == 400
    assert client.post("/api/player/play", data="not json").status_code == 400
    assert client.post("/api/player/volume", json={"volume": 50}).status_code == 200
