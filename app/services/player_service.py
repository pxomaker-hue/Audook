"""
Player service - manages playback and progress
"""

from typing import Optional, Callable
from app.player import player, progress_manager
from app.models import Audiobook
from app.utils import logger
from app.sync import progress_sync

# Consider the current chapter "fully listened" (for auto mark-as-finished)
# once we're this close to the end of the last chapter.
AUTO_FINISH_THRESHOLD_SECONDS = 2.0


class PlayerService:
    """Service for managing audio playback"""

    def __init__(self):
        self.current_audiobook: Optional[Audiobook] = None
        self.current_chapter_index: int = 0
        self._on_position_changed: Optional[Callable] = None
        self._auto_finished: bool = False

    def start_playbook(
        self,
        audiobook: Audiobook,
        device_id: str = "audook_windows",
        chapter_index: Optional[int] = None,
        position: Optional[float] = None,
    ) -> bool:
        """Start playing an audiobook, optionally jumping straight to a given
        chapter/position (e.g. resuming a bookmark)"""
        try:
            if not audiobook or not audiobook.chapters:
                logger.error("No audiobook or chapters to play")
                return False

            self.current_audiobook = audiobook
            self._auto_finished = False

            if chapter_index is not None:
                chapter_idx = max(0, min(chapter_index, len(audiobook.chapters) - 1))
                position = position if position is not None else 0.0
            else:
                # Load saved local progress, then check whether the source
                # server (Plex/ABS) has a more advanced position - e.g. this
                # book was also listened to from the official app/website.
                chapter_idx, position = progress_manager.load_progress(audiobook)
                chapter_idx, position = self._merge_remote_progress(audiobook, chapter_idx, position)
            self.current_chapter_index = chapter_idx

            # Start session
            progress_manager.start_session(audiobook, chapter_idx, position, device_id)

            # Start playback
            if chapter_idx < len(audiobook.chapters):
                chapter = audiobook.chapters[chapter_idx]
                success = player.play(audiobook, chapter, position)

                if success:
                    logger.info(f"Started playing: {audiobook.title}")
                    # Setup position updates and chapter auto-advance
                    player.on_position_change(self._on_player_position_changed)
                    player.on_playback_end(self._on_chapter_ended)
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to start playbook: {e}")
            return False

    def _merge_remote_progress(self, audiobook: Audiobook, chapter_idx: int, position: float):
        """Compare local progress against the source server's and use
        whichever is further along - best-effort, silently keeps the local
        values on any failure (offline, local-folder book, etc)."""
        try:
            remote = progress_sync.pull_progress(audiobook.id)
            if not remote:
                return chapter_idx, position

            def cumulative(idx: int, pos: float) -> float:
                total = 0.0
                for i, chapter in enumerate(audiobook.chapters or []):
                    if i < idx:
                        total += chapter.get("duration", 0) or 0
                    elif i == idx:
                        total += pos
                        break
                return total

            local_cum = cumulative(chapter_idx, position)
            remote_cum = cumulative(remote["chapter_index"], remote["position_seconds"])

            if remote_cum > local_cum + 1.0:
                logger.info(f"Using more advanced remote progress for {audiobook.title}")
                return remote["chapter_index"], remote["position_seconds"]
        except Exception as e:
            logger.warning(f"Failed to merge remote progress: {e}")

        return chapter_idx, position

    def pause(self) -> bool:
        """Pause playback"""
        try:
            if player.pause():
                progress_manager.mark_paused()
                progress_manager.push_remote_now()
                logger.info("Playback paused")
                return True
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
        return False

    def resume(self) -> bool:
        """Resume playback"""
        try:
            if player.resume():
                progress_manager.mark_resumed()

                # A pause that ran long enough auto-closes its session (see
                # ProgressManager.PAUSE_TIMEOUT_SECONDS) - reopen a fresh one.
                if not progress_manager.is_session_active() and self.current_audiobook:
                    progress_manager.start_session(
                        self.current_audiobook,
                        self.current_chapter_index,
                        player.get_position(),
                        device_id="audook_windows"
                    )

                logger.info("Playback resumed")
                return True
        except Exception as e:
            logger.error(f"Failed to resume: {e}")
        return False

    def stop(self) -> bool:
        """Stop playback and clear the loaded book, so the player goes back
        to its empty state instead of showing a book that can no longer be
        resumed (resume only works on a paused player, not a stopped one)."""
        try:
            progress_manager.end_session()
            player.stop()
            self.current_audiobook = None
            self.current_chapter_index = 0
            logger.info("Playback stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop: {e}")
            return False

    def seek(self, position_seconds: float) -> bool:
        """Seek to position"""
        try:
            if player.seek(position_seconds):
                progress_manager.update_progress(self.current_chapter_index, position_seconds)
                return True
        except Exception as e:
            logger.error(f"Failed to seek: {e}")
        return False

    def seek_relative(self, seconds: float) -> bool:
        """Seek relative to current position"""
        try:
            if player.seek_relative(seconds):
                current_pos = player.get_position()
                progress_manager.update_progress(self.current_chapter_index, current_pos)
                return True
        except Exception as e:
            logger.error(f"Failed to seek relative: {e}")
        return False

    def next_chapter(self) -> bool:
        """Play next chapter"""
        try:
            if player.next_chapter():
                self.current_chapter_index += 1
                progress_manager.update_progress(self.current_chapter_index, 0.0)
                logger.info(f"Playing chapter {self.current_chapter_index}")
                return True
        except Exception as e:
            logger.error(f"Failed to go to next chapter: {e}")
        return False

    def previous_chapter(self) -> bool:
        """Play previous chapter"""
        try:
            if player.previous_chapter():
                self.current_chapter_index = max(0, self.current_chapter_index - 1)
                progress_manager.update_progress(self.current_chapter_index, 0.0)
                logger.info(f"Playing chapter {self.current_chapter_index}")
                return True
        except Exception as e:
            logger.error(f"Failed to go to previous chapter: {e}")
        return False

    def set_volume(self, volume: float) -> bool:
        """Set playback volume (0-100)"""
        try:
            return player.set_volume(volume)
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False

    def set_speed(self, speed: float) -> bool:
        """Set playback speed (0.5-2.0)"""
        try:
            return player.set_speed(speed)
        except Exception as e:
            logger.error(f"Failed to set speed: {e}")
            return False

    def get_current_position(self) -> float:
        """Get current position in seconds"""
        return player.get_position()

    def get_current_duration(self) -> float:
        """Get current chapter duration"""
        return player.get_duration()

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return player.is_playing()

    def is_paused(self) -> bool:
        """Check if paused"""
        return player.is_paused()

    def on_position_changed(self, callback: Callable[[float, float], None]):
        """Set callback for position updates (position, duration)"""
        self._on_position_changed = callback

    def _on_player_position_changed(self, position: float):
        """Handle position change from VLC player"""
        duration = player.get_duration()

        # Update progress in background
        progress_manager.update_progress(self.current_chapter_index, position)

        # Auto mark-as-finished: reached the end of the last chapter
        if (
            not self._auto_finished
            and self.current_audiobook
            and self.current_audiobook.chapters
            and self.current_chapter_index == len(self.current_audiobook.chapters) - 1
            and duration > 0
            and position >= duration - AUTO_FINISH_THRESHOLD_SECONDS
        ):
            self._auto_finished = True
            progress_manager.mark_as_finished(self.current_audiobook)
            progress_manager.push_remote_now(finished=True)

        # Notify UI
        if self._on_position_changed:
            try:
                self._on_position_changed(position, duration)
            except Exception as e:
                logger.error(f"Position callback error: {e}")

    def _on_chapter_ended(self):
        """A chapter finished playing on its own (end of media, not a user
        pause/stop) - advance to the next one, or end the session cleanly if
        that was the last chapter (already marked as finished above)."""
        try:
            if not self.current_audiobook or not self.current_audiobook.chapters:
                return

            is_last_chapter = self.current_chapter_index >= len(self.current_audiobook.chapters) - 1
            if is_last_chapter:
                progress_manager.end_session()
                return

            self.next_chapter()
        except Exception as e:
            logger.error(f"Failed to auto-advance after chapter end: {e}")


# Global instance
player_service = PlayerService()
