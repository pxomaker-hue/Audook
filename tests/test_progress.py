"""POST /api/books/<id>/progress: whole-book percentage (not per chapter),
finished threshold, validation."""
import pytest

from app.database import get_session, ReadingProgressRepository


@pytest.fixture(autouse=True)
def no_remote_push(monkeypatch):
    monkeypatch.setattr("app.api.progress.progress_sync.push_progress", lambda *a, **k: None)


def post(client, book_id, chapter, position):
    return client.post(f"/api/books/{book_id}/progress",
                       json={"chapter_index": chapter, "position_seconds": position})


def test_percentage_is_computed_over_the_whole_book(client, seed_book):
    book_id = seed_book(durations=(100.0, 200.0, 300.0))  # total 600
    # chapter 1 (0-based), 50s in -> (100 + 50) / 600
    data = post(client, book_id, 1, 50).get_json()
    assert data["percentage"] == pytest.approx(25.0)
    assert data["is_finished"] is False


def test_progress_is_persisted(client, seed_book):
    book_id = seed_book()
    post(client, book_id, 2, 10)
    progress = ReadingProgressRepository(get_session()).get_or_create(book_id)
    assert progress.current_chapter_index == 2
    assert progress.position_seconds == 10


def test_book_is_marked_finished_from_99_percent(client, seed_book):
    book_id = seed_book(durations=(100.0, 100.0))
    data = post(client, book_id, 1, 99).get_json()  # 199/200 = 99.5%
    assert data["is_finished"] is True
    assert ReadingProgressRepository(get_session()).get_or_create(book_id).is_finished is True


def test_percentage_is_clamped_to_100(client, seed_book):
    book_id = seed_book(durations=(100.0,))
    assert post(client, book_id, 0, 5000).get_json()["percentage"] == 100.0


def test_missing_fields_are_rejected(client, seed_book):
    book_id = seed_book()
    assert client.post(f"/api/books/{book_id}/progress", json={"chapter_index": 0}).status_code == 400


def test_unknown_book_is_404(client, db):
    assert post(client, "nope", 0, 0).status_code == 404


def test_delete_progress_resets_book(client, seed_book):
    book_id = seed_book()
    post(client, book_id, 1, 30)
    assert client.delete(f"/api/books/{book_id}/progress").status_code == 200
    assert ReadingProgressRepository(get_session()).get_current_position(book_id) == 0
