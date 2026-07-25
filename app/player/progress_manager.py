"""
Reading progress manager
Handles saving/loading progress and syncing with database
"""

from typing import Optional, Dict, Any
from datetime import datetime
import threading
import time

from app.database import get_session, ReadingProgressRepository, ReadingHistoryRepository
from app.models import Audiobook
from app.utils import logger


class ProgressManager:
    """Manages reading progress tracking and database persistence"""

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

        # Session tracking
        self._current_session_id: Optional[int] = None
        self._session_active: bool = False

        # Auto-save thread
        self._save_thread: Optional[threading.Thread] = None
        self._stop_save_thread: bool = False

    def start_session(self, audiobook: Audiobook, chapter_index: int, position: float, device_id: str = None) -> int:
        """
        Start a new reading session

        Args:
            audiobook: The audiobook being read
            chapter_index: Current chapter index
            position: Starting position in seconds
            device_id: Device identifier for multi-device sync

        Returns:
            Session ID
        """
        self._current_audiobook = audiobook
        self._current_chapter_index = chapter_index
        self._current_position = position
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

    def end_session(self):
        """End current reading session"""
        if not self._session_active:
            return

        self._session_active = False
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
            repo = ReadingProgressRepository(session)

            progress = repo.session.query(repo.__class__.__bases__[0]).filter_by(
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
        """Continuously save progress at intervals"""
        while not self._stop_save_thread and self._session_active:
            try:
                self.save_progress()
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
