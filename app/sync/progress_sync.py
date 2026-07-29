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

# A push whose new position is more than this far BEHIND the position
# already recorded on the source server is treated as a stray/test session
# rather than an intentional rewind, and is skipped - remote pushes are
# otherwise unconditional, so a mobile test session (even a few seconds,
# even paused right away) was silently overwriting real listening progress
# that only lived on Audiobookshelf/Plex. A genuine large rewind (e.g.
# dragging the progress bar far back) is rare enough that losing one remote
# sync for it is an acceptable trade-off - the next push past that point
# corrects it. Never applied when marking a book finished (always intentional).
REGRESSION_GUARD_SECONDS = 150

# One authenticated Audiobookshelf client per server, reused across pushes/
# pulls instead of logging in fresh every call - progress pushes happen
# every ~15-20s during playback, and repeated POST /login calls were enough
# to trip Audiobookshelf's own rate limiter (see scanner.py's own client
# reuse for the same reason), which made pushes fail silently - caught
# below and merely logged as a warning - rather than actually reaching the
# server.
_abs_clients: Dict[str, AudiobookshelfClient] = {}


def _get_abs_client(server, force_new: bool = False) -> AudiobookshelfClient:
    if not force_new and server.id in _abs_clients:
        return _abs_clients[server.id]
    client = AudiobookshelfClient(ServerRepository.active_url(server), server.username, server.password)
    _abs_clients[server.id] = client
    return client


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
        new_cumulative = _cumulative_seconds(book.chapters or [], chapter_index, position_seconds)

        if server.type == "plex":
            client = PlexClient(server.url, server.api_key)
            if not finished:
                remote = client.pull_progress(book_id, book.chapters or [])
                if remote and not remote.get("finished"):
                    remote_cumulative = _cumulative_seconds(
                        book.chapters or [], remote["chapter_index"], remote["position_seconds"]
                    )
                    if remote_cumulative - new_cumulative > REGRESSION_GUARD_SECONDS:
                        logger.warning(
                            f"Skipping remote progress push for {book_id}: would regress Plex "
                            f"progress by {remote_cumulative - new_cumulative:.0f}s"
                        )
                        return False
            return client.push_progress(book_id, book.chapters or [], chapter_index, position_seconds, finished)

        if server.type == "audiobookshelf":
            item_id = book_id.replace("abs_", "", 1)

            try:
                client = _get_abs_client(server)
                remote = None if finished else client.get_user_progress(item_id)
            except Exception:
                # Cached client's token may have gone stale - one retry with
                # a fresh login before giving up on this push.
                client = _get_abs_client(server, force_new=True)
                remote = None if finished else client.get_user_progress(item_id)

            if remote and not remote.get("finished"):
                remote_cumulative = remote.get("position_seconds", 0.0)
                if remote_cumulative - new_cumulative > REGRESSION_GUARD_SECONDS:
                    logger.warning(
                        f"Skipping remote progress push for {book_id}: would regress Audiobookshelf "
                        f"progress by {remote_cumulative - new_cumulative:.0f}s (from "
                        f"{remote_cumulative:.0f}s to {new_cumulative:.0f}s) - looks like a stray/test "
                        f"session rather than an intentional rewind."
                    )
                    return False

            client.set_user_progress(item_id, new_cumulative, book.duration or 0.0, finished)
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
            client = _get_abs_client(server)
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
