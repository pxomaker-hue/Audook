"""
Bidirectional progress sync between Audook and the source server
(Plex / Audiobookshelf). Best-effort only: local-folder books have no
remote to sync with, and any network/API failure here must never break
local playback.
"""

from typing import Optional, Dict, Any, List

from app.database import get_session, ServerRepository, BookRepository
from app.clients import PlexClient, AudiobookshelfClient
from app.utils import logger


def _cumulative_seconds(chapters: List[Dict[str, Any]], chapter_index: int, position_in_chapter: float) -> float:
    """Convert (chapter_index, position within that chapter) into a single
    cumulative position across the whole book - the shape Audiobookshelf
    expects."""
    total = 0.0
    for i, chapter in enumerate(chapters or []):
        if i < chapter_index:
            total += chapter.get("duration", 0) or 0
        elif i == chapter_index:
            total += position_in_chapter
            break
    return total


def _split_cumulative(chapters: List[Dict[str, Any]], cumulative_seconds: float) -> tuple:
    """Inverse of _cumulative_seconds: turn a whole-book cumulative position
    back into (chapter_index, position_in_chapter)."""
    remaining = cumulative_seconds
    chapters = chapters or []
    for i, chapter in enumerate(chapters):
        duration = chapter.get("duration", 0) or 0
        if remaining <= duration or i == len(chapters) - 1:
            return i, max(0.0, remaining)
        remaining -= duration
    return 0, 0.0


def push_progress(book_id: str, chapter_index: int, position_seconds: float, finished: bool = False) -> bool:
    """Best-effort push of local progress to the book's source server."""
    session = get_session()
    try:
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return False
        server = ServerRepository(session).get_by_id(book.server_id)
        if not server:
            return False

        if server.type == "plex":
            client = PlexClient(server.url, server.api_key)
            return client.push_progress(book_id, book.chapters or [], chapter_index, position_seconds, finished)

        if server.type == "audiobookshelf":
            client = AudiobookshelfClient(server.url, server.username, server.password)
            item_id = book_id.replace("abs_", "", 1)
            cumulative = _cumulative_seconds(book.chapters or [], chapter_index, position_seconds)
            client.set_user_progress(item_id, cumulative, book.duration or 0.0, finished)
            return True

        return False
    except Exception as e:
        logger.warning(f"Failed to push progress for {book_id}: {e}")
        return False
    finally:
        session.close()


def pull_progress(book_id: str) -> Optional[Dict[str, Any]]:
    """Best-effort fetch of the book's progress from its source server.
    Returns {chapter_index, position_seconds, finished} or None if
    unavailable (local book, no remote progress, or a network failure)."""
    session = get_session()
    try:
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return None
        server = ServerRepository(session).get_by_id(book.server_id)
        if not server:
            return None

        if server.type == "plex":
            client = PlexClient(server.url, server.api_key)
            return client.pull_progress(book_id, book.chapters or [])

        if server.type == "audiobookshelf":
            client = AudiobookshelfClient(server.url, server.username, server.password)
            item_id = book_id.replace("abs_", "", 1)
            remote = client.get_user_progress(item_id)
            if not remote:
                return None
            chapter_index, position = _split_cumulative(book.chapters or [], remote.get("position_seconds", 0.0))
            return {"chapter_index": chapter_index, "position_seconds": position, "finished": remote.get("finished", False)}

        return None
    except Exception as e:
        logger.warning(f"Failed to pull progress for {book_id}: {e}")
        return None
    finally:
        session.close()
