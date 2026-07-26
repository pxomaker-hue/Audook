"""
Reading progress manager
Handles saving/loading progress and syncing with database
"""

from typing import Optional, Dict, Any
from datetime import datetime
import threading
import time

from app.database import get_session, ReadingProgressRepository, ReadingHistoryRepository
from app.database.models import ReadingProgress
from app.models import Audiobook
from app.utils import logger


class ProgressManager:
    """Manages reading progress tracking and database persistence"""

    # How long a session can stay paused before it's considered over. Resuming
    # after this opens a fresh session rather than continuing the old one, so
    # a session's duration reflects actual listening time, not idle gaps.
    PAUSE_TIMEOUT_SECONDS = 15 * 60

    def __init__(self, save_interval: int = 5):
        """
        Initialize progress manager

        Args:
            save_interval: Seconds between auto-saves to database
        """
        self.save_interval = save_interval
        self._current_audiobook: Optional[Audiobook] = None
        self._current_chapter_index: int = 0
        self._current_position: float = 0.0
        self._device_id: Optional[str] = None

        # Session tracking
        self._current_session_id: Optional[int] = None
        self._session_active: bool = False
        self._paused_since: Optional[float] = None

        # Auto-save thread
        self._save_thread: Optional[threading.Thread] = None
        self._stop_save_thread: bool = False

    def start_session(self, audiobook: Audiobook, chapter_index: int, position: float, device_id: str = None) -> int:
        """
        Start (or continue) a reading session.

        Reuses the current history row when it's already tracking the same
        book - repeated "Lire" clicks, chapter changes, etc. shouldn't spawn a
        new history entry each time. Switching to a different book properly
        closes out the previous one first.

        Args:
            audiobook: The audiobook being read
            chapter_index: Current chapter index
            position: Starting position in seconds
            device_id: Device identifier for multi-device sync

        Returns:
            Session ID
        """
        same_book_session_active = (
            self._session_active
            and self._current_audiobook is not None
            and self._current_audiobook.id == audiobook.id
        )

        if self._session_active and not same_book_session_active:
            # A different book was playing - close it out with an accurate
            # duration before starting the new one.
            self.end_session()

        self._current_audiobook = audiobook
        self._current_chapter_index = chapter_index
        self._current_position = position
        self._device_id = device_id
        self._paused_since = None

        if same_book_session_active:
            return self._current_session_id

        self._session_active = True

        try:
            session = get_session()
            repo = ReadingHistoryRepository(session)
            history = repo.create_session(audiobook.id, position, chapter_index, device_id)
            self._current_session_id = history.id
            session.close()

            logger.info(f"Session started: {audiobook.title} - Chapter {chapter_index}")

            # Start auto-save thread
            self._start_auto_save()

            return history.id
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return -1

    def update_progress(self, chapter_index: int, position: float):
        """Update current progress"""
        self._current_chapter_index = chapter_index
        self._current_position = position

    def mark_paused(self):
        """Record that playback was paused, for the pause-timeout check"""
        if self._paused_since is None:
            self._paused_since = time.time()

    def mark_resumed(self):
        """Record that playback resumed"""
        self._paused_since = None

    def is_session_active(self) -> bool:
        """Whether a reading session is currently open"""
        return self._session_active

    def _checkpoint_history(self):
        """Refresh the current history row's end time/position without
        closing the session, so an abrupt shutdown loses at most
        `save_interval` seconds of data instead of the whole session."""
        if not self._session_active or self._current_session_id is None or self._current_session_id == -1:
            return
        try:
            session = get_session()
            repo = ReadingHistoryRepository(session)
            repo.end_session(self._current_session_id, self._current_position, self._current_chapter_index)
            session.close()
        except Exception as e:
            logger.error(f"Failed to checkpoint history: {e}")

    def end_session(self):
        """End current reading session"""
        if not self._session_active:
            return

        self._session_active = False
        self._paused_since = None

        # The auto-save thread calls end_session() on itself when a pause
        # times out; joining it from inside its own thread would deadlock.
        # It exits on its own right after via the `_session_active` check.
        if threading.current_thread() is not self._save_thread:
            self._stop_auto_save()

        try:
            session = get_session()
            repo = ReadingHistoryRepository(session)
            repo.end_session(
                self._current_session_id,
                self._current_position,
                self._current_chapter_index
            )
            session.close()

            logger.info(f"Session ended: {self._current_session_id}")
        except Exception as e:
            logger.error(f"Failed to end session: {e}")

    def save_progress(self) -> bool:
        """Save current progress to database"""
        if not self._current_audiobook:
            return False

        try:
            session = get_session()
            repo = ReadingProgressRepository(session)

            # Calculate progress percentage
            total_duration = self._current_audiobook.duration
            progress_percent = (self._current_position / total_duration * 100) if total_duration > 0 else 0

            repo.update_progress(
                self._current_audiobook.id,
                self._current_chapter_index,
                self._current_position,
                progress_percent
            )
            session.close()

            return True
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            return False

    def load_progress(self, audiobook: Audiobook) -> tuple[int, float]:
        """
        Load saved progress for an audiobook

        Args:
            audiobook: The audiobook to load progress for

        Returns:
            Tuple of (chapter_index, position_seconds)
        """
        try:
            session = get_session()

            progress = session.query(ReadingProgress).filter_by(
                book_id=audiobook.id
            ).first()

            if not progress:
                session.close()
                return (0, 0.0)

            chapter_index = progress.current_chapter_index
            position = progress.position_seconds
            session.close()

            logger.info(f"Loaded progress: {audiobook.title} - Chapter {chapter_index}, {position}s")
            return (chapter_index, position)

        except Exception as e:
            logger.error(f"Failed to load progress: {e}")
            return (0, 0.0)

    def _start_auto_save(self):
        """Start auto-save thread"""
        self._stop_save_thread = False
        self._save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self._save_thread.start()

    def _stop_auto_save(self):
        """Stop auto-save thread"""
        self._stop_save_thread = True
        if self._save_thread:
            self._save_thread.join(timeout=2.0)

    def _auto_save_loop(self):
        """Continuously save progress at intervals, and refresh the current
        history row's end time so an abrupt shutdown loses very little.
        Closes the session outright if it's been paused too long."""
        while not self._stop_save_thread and self._session_active:
            try:
                self.save_progress()

                if self._paused_since and (time.time() - self._paused_since) > self.PAUSE_TIMEOUT_SECONDS:
                    logger.info("Reading session auto-closed after an extended pause")
                    self.end_session()
                    break

                self._checkpoint_history()
            except Exception as e:
                logger.error(f"Auto-save error: {e}")

            time.sleep(self.save_interval)

    def get_reading_history(self, audiobook: Audiobook, limit: int = 10) -> list:
        """Get reading history for an audiobook"""
        try:
            session = get_session()
            repo = ReadingHistoryRepository(session)
            history = repo.get_by_book(audiobook.id, limit)
            session.close()
            return history
        except Exception as e:
            logger.error(f"Failed to get reading history: {e}")
            return []

    def mark_as_finished(self, audiobook: Audiobook):
        """Mark an audiobook as finished"""
        try:
            session = get_session()
            repo = ReadingProgressRepository(session)
            repo.mark_finished(audiobook.id)
            session.close()

            logger.info(f"Marked as finished: {audiobook.title}")
        except Exception as e:
            logger.error(f"Failed to mark as finished: {e}")


# Global progress manager instance
progress_manager = ProgressManager()
