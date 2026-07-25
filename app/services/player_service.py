"""
Player service - manages playback and progress
"""

from typing import Optional, Callable
from app.player import player, progress_manager
from app.models import Audiobook
from app.utils import logger


class PlayerService:
    """Service for managing audio playback"""

    def __init__(self):
        self.current_audiobook: Optional[Audiobook] = None
        self.current_chapter_index: int = 0
        self._on_position_changed: Optional[Callable] = None

    def start_playbook(self, audiobook: Audiobook, device_id: str = "audook_windows") -> bool:
        """Start playing an audiobook"""
        try:
            if not audiobook or not audiobook.chapters:
                logger.error("No audiobook or chapters to play")
                return False

            self.current_audiobook = audiobook

            # Load saved progress
            chapter_idx, position = progress_manager.load_progress(audiobook)
            self.current_chapter_index = chapter_idx

            # Start session
            progress_manager.start_session(audiobook, chapter_idx, position, device_id)

            # Start playback
            if chapter_idx < len(audiobook.chapters):
                chapter = audiobook.chapters[chapter_idx]
                success = player.play(audiobook, chapter, position)

                if success:
                    logger.info(f"Started playing: {audiobook.title}")
                    # Setup position updates
                    player.on_position_change(self._on_player_position_changed)
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to start playbook: {e}")
            return False

    def pause(self) -> bool:
        """Pause playback"""
        try:
            if player.pause():
                logger.info("Playback paused")
                return True
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
        return False

    def resume(self) -> bool:
        """Resume playback"""
        try:
            if player.resume():
                logger.info("Playback resumed")
                return True
        except Exception as e:
            logger.error(f"Failed to resume: {e}")
        return False

    def stop(self) -> bool:
        """Stop playback"""
        try:
            progress_manager.end_session()
            player.stop()
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

        # Notify UI
        if self._on_position_changed:
            try:
                self._on_position_changed(position, duration)
            except Exception as e:
                logger.error(f"Position callback error: {e}")


# Global instance
player_service = PlayerService()
