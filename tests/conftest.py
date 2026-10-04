"""Shared pytest setup for the backend tests.

app/__init__.py creates ~/.Audook at import time, so HOME/USERPROFILE must
point at a throwaway directory BEFORE anything from `app` is imported -
otherwise the tests would read/write the developer's real library database.
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="audook-test-home-")
os.environ["HOME"] = _TMP_HOME
os.environ["USERPROFILE"] = _TMP_HOME

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from app.database import init_database, get_session, ServerRepository, BookRepository  # noqa: E402
from app.database.models import Library  # noqa: E402


@pytest.fixture(scope="session")
def backend():
    import audook_backend
    return audook_backend


@pytest.fixture()
def db(tmp_path):
    """A fresh empty SQLite database for each test."""
    database = init_database(str(tmp_path / "test.db"))
    yield database
    database.engine.dispose()


@pytest.fixture()
def client(backend, db):
    backend.app.config["TESTING"] = True
    # The lazy service init (PlayerService/VLC, background sync) is irrelevant
    # to routing/DB tests - the library service is real (plain DB reads),
    # player/sync are stand-ins.
    from app.api.context import services

    class _Stub:
        def __getattr__(self, name):
            return lambda *a, **k: None

    previous = (services.library, services.player, services.sync)
    from app.services import LibraryService
    services.library, services.player, services.sync = LibraryService(), _Stub(), _Stub()
    yield backend.app.test_client()
    services.library, services.player, services.sync = previous


@pytest.fixture()
def seed_book(db):
    """Returns a function creating a server+library+book and returning the book id."""
    def _seed(book_id="b1", durations=(100.0, 200.0, 300.0), server_type="local", url="/tmp/none"):
        session = get_session()
        if not ServerRepository(session).get_by_id("srv1"):
            ServerRepository(session).create("srv1", server_type, "Test server", url)
            session.add(Library(id="lib1", server_id="srv1", name="Lib", source=server_type))
            session.commit()
        chapters = [
            {"title": f"Chapter {i + 1}", "duration": d, "audio_file": f"/tmp/ch{i}.mp3"}
            for i, d in enumerate(durations)
        ]
        BookRepository(session).create(
            book_id, "srv1", "lib1", "Test Book", author="Author",
            duration=sum(durations), chapters=chapters,
        )
        return book_id
    return _seed
