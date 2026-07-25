"""
Audio player for Audook
Handles audio playback with pygame
"""

import pygame
import pygame.mixer
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import threading
import time
from datetime import datetime

from app.models import Audiobook
from app.utils import logger
from app.utils.config_manager import config_manager


class AudioPlayer:
    """Audio player using pygame mixer"""

    def __init__(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

        self._current_audiobook: Optional[Audiobook] = None
        self._current_chapter: Optional[Dict[str, Any]] = None
        self._current_position: float = 0.0
        self._is_playing: bool = False
        self._volume: float = 0.8
        self._speed: float = 1.0
        self._paused: bool = False
        self._current_sound: Optional[pygame.mixer.Sound] = None

        # Callbacks
        self._on_playback_start: Optional[Callable] = None
        self._on_playback_pause: Optional[Callable] = None
        self._on_playback_resume: Optional[Callable] = None
        self._on_playback_stop: Optional[Callable] = None
        self._on_position_change: Optional[Callable[[float], None]] = None
        self._on_chapter_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_playback_end: Optional[Callable] = None

        # Thread for position tracking
        self._position_thread: Optional[threading.Thread] = None
        self._stop_position_thread: bool = False
        self._last_position_update: float = 0.0

        # Initialize
        self.set_volume(config_manager.config.volume)
        self.set_speed(config_manager.config.playback_speed)

        # Start position update thread
        self._start_position_thread()

    def _start_position_thread(self):
        """Start the position update thread"""
        self._stop_position_thread = False
        self._position_thread = threading.Thread(target=self._position_update_loop, daemon=True)
        self._position_thread.start()

    def _position_update_loop(self):
        """Loop to update position regularly"""
        while not self._stop_position_thread:
            if self._is_playing and not self._paused and self._current_sound:
                # For pygame mixer, we need to track position manually
                if self._current_sound.get_busy():
                    elapsed = time.time() - self._last_position_update
                    if elapsed > 0.1:
                        self._current_position += elapsed * self._speed
                        self._last_position_update = time.time()

                        # Notify position change
                        if self._on_position_change:
                            try:
                                self._on_position_change(self._current_position)
                            except Exception as e:
                                logger.error(f"Position callback error: {e}")

                        # Save state periodically
                        if self._current_audiobook and self._current_chapter:
                            self._save_playback_state()
                else:
                    # Sound has ended, play next chapter
                    self._handle_playback_end()

            time.sleep(0.1)

    def _save_playback_state(self):
        """Save current playback state"""
        if not self._current_audiobook or not self._current_chapter:
            return

        try:
            from app.models import PlaybackState

            state = PlaybackState(
                book_id=self._current_audiobook.id,
                library_id=self._current_audiobook.library_id,
                chapter_id=self._current_chapter.get("id"),
                position=self._current_position,
                is_playing=self._is_playing and not self._paused,
                speed=self._speed,
            )
            config_manager.update_playback_state(state)
        except Exception as e:
            logger.error(f"Failed to save playback state: {e}")

    def _load_playback_state(self, audiobook: Audiobook, chapter: Dict[str, Any]) -> float:
        """Load saved playback state for a book/chapter"""
        try:
            if config_manager.playback_state:
                if (config_manager.playback_state.book_id == audiobook.id
                    and config_manager.playback_state.library_id == audiobook.library_id):
                    return config_manager.playback_state.position
        except Exception as e:
            logger.error(f"Failed to load playback state: {e}")
        return 0.0

    def play(self, audiobook: Audiobook, chapter: Dict[str, Any], start_position: float = 0.0) -> bool:
        """Play an audiobook chapter"""
        if not audiobook or not chapter:
            logger.warning("No audiobook or chapter to play")
            return False

        # Stop current playback
        self.stop()

        # Set new audiobook and chapter
        self._current_audiobook = audiobook
        self._current_chapter = chapter

        # Load saved position or use provided position
        if start_position == 0.0:
            self._current_position = self._load_playback_state(audiobook, chapter)
        else:
            self._current_position = start_position

        # Get audio file path
        audio_file_path = chapter.get("audio_file", "")

        if not audio_file_path:
            logger.error("No audio file path for chapter")
            return False

        # Check if file exists (for local files)
        if not Path(audio_file_path).exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return False

        try:
            # Load the sound
            self._current_sound = pygame.mixer.Sound(audio_file_path)

            # Set volume
            self._current_sound.set_volume(self._volume)

            # Start playback
            self._current_sound.play()
            self._is_playing = True
            self._paused = False
            self._last_position_update = time.time()

            logger.info(f"Playing {audiobook.title} - {chapter.get('title')}")

            # Notify start
            if self._on_playback_start:
                try:
                    self._on_playback_start()
                except Exception as e:
                    logger.error(f"Playback start callback error: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False

    def pause(self) -> bool:
        """Pause playback"""
        if not self._is_playing:
            return False

        try:
            if self._current_sound:
                pygame.mixer.pause()
                self._paused = True

                if self._on_playback_pause:
                    try:
                        self._on_playback_pause()
                    except Exception as e:
                        logger.error(f"Pause callback error: {e}")

                return True
        except Exception as e:
            logger.error(f"Pause error: {e}")

        return False

    def resume(self) -> bool:
        """Resume playback"""
        if not self._paused:
            return False

        try:
            pygame.mixer.unpause()
            self._paused = False
            self._last_position_update = time.time()

            if self._on_playback_resume:
                try:
                    self._on_playback_resume()
                except Exception as e:
                    logger.error(f"Resume callback error: {e}")

            return True
        except Exception as e:
            logger.error(f"Resume error: {e}")

        return False

    def stop(self) -> bool:
        """Stop playback"""
        if not self._is_playing:
            return False

        try:
            pygame.mixer.stop()
            self._is_playing = False
            self._paused = False
            self._current_sound = None

            # Save state
            if self._current_audiobook and self._current_chapter:
                self._save_playback_state()

            if self._on_playback_stop:
                try:
                    self._on_playback_stop()
                except Exception as e:
                    logger.error(f"Stop callback error: {e}")

            return True
        except Exception as e:
            logger.error(f"Stop error: {e}")

        return False

    def seek(self, position: float) -> bool:
        """Seek to a position in the current chapter"""
        if not self._current_sound:
            return False

        try:
            # Clamp position to chapter duration
            chapter_duration = self._current_chapter.get("duration", 0) if self._current_chapter else 0
            position = max(0.0, min(position, chapter_duration))

            # pygame mixer doesn't support seeking, so we need to stop and restart
            # This is a limitation of pygame - a real implementation would use a different library
            if self._is_playing:
                self.stop()
                self._current_position = position
                self.play(self._current_audiobook, self._current_chapter, position)
            else:
                self._current_position = position

            return True
        except Exception as e:
            logger.error(f"Seek error: {e}")
            return False

    def seek_relative(self, seconds: float) -> bool:
        """Seek relative to current position"""
        if not self._current_chapter:
            return False

        chapter_duration = self._current_chapter.get("duration", 0)
        new_position = self._current_position + seconds

        return self.seek(new_position)

    def set_volume(self, volume: float) -> bool:
        """Set volume (0.0 to 1.0)"""
        try:
            self._volume = max(0.0, min(1.0, volume))
            if self._current_sound:
                self._current_sound.set_volume(self._volume)
            pygame.mixer.set_volume(self._volume)
            config_manager.config.volume = self._volume
            return True
        except Exception as e:
            logger.error(f"Set volume error: {e}")
            return False

    def set_speed(self, speed: float) -> bool:
        """Set playback speed (0.5 to 2.0)"""
        try:
            self._speed = max(0.5, min(2.0, speed))
            config_manager.config.playback_speed = self._speed
            # Note: pygame mixer doesn't support speed control
            # A real implementation would use a different library
            return True
        except Exception as e:
            logger.error(f"Set speed error: {e}")
            return False

    def get_volume(self) -> float:
        """Get current volume"""
        return self._volume

    def get_speed(self) -> float:
        """Get current playback speed"""
        return self._speed

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self._is_playing and not self._paused

    def is_paused(self) -> bool:
        """Check if paused"""
        return self._paused

    def get_current_position(self) -> float:
        """Get current playback position"""
        return self._current_position

    def next_chapter(self) -> bool:
        """Play next chapter"""
        if not self._current_audiobook:
            return False

        chapters = self._current_audiobook.chapters
        if not chapters:
            return False

        current_idx = next(
            (i for i, ch in enumerate(chapters) if ch.get("id") == self._current_chapter.get("id")),
            -1
        )

        if current_idx >= 0 and current_idx < len(chapters) - 1:
            next_chapter = chapters[current_idx + 1]
            return self.play(self._current_audiobook, next_chapter, 0.0)

        return False

    def previous_chapter(self) -> bool:
        """Play previous chapter"""
        if not self._current_audiobook:
            return False

        chapters = self._current_audiobook.chapters
        if not chapters:
            return False

        current_idx = next(
            (i for i, ch in enumerate(chapters) if ch.get("id") == self._current_chapter.get("id")),
            -1
        )

        if current_idx > 0:
            prev_chapter = chapters[current_idx - 1]
            return self.play(self._current_audiobook, prev_chapter, 0.0)

        return False

    def _handle_playback_end(self):
        """Handle end of chapter playback"""
        if self._on_playback_end:
            try:
                self._on_playback_end()
            except Exception as e:
                logger.error(f"Playback end callback error: {e}")

        # Try to play next chapter
        if not self.next_chapter():
            self.stop()

    def set_on_playback_start(self, callback: Callable):
        """Set callback for playback start"""
        self._on_playback_start = callback

    def set_on_playback_pause(self, callback: Callable):
        """Set callback for playback pause"""
        self._on_playback_pause = callback

    def set_on_playback_resume(self, callback: Callable):
        """Set callback for playback resume"""
        self._on_playback_resume = callback

    def set_on_playback_stop(self, callback: Callable):
        """Set callback for playback stop"""
        self._on_playback_stop = callback

    def set_on_position_change(self, callback: Callable[[float], None]):
        """Set callback for position change"""
        self._on_position_change = callback

    def set_on_chapter_change(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for chapter change"""
        self._on_chapter_change = callback

    def set_on_playback_end(self, callback: Callable):
        """Set callback for playback end"""
        self._on_playback_end = callback

    def shutdown(self):
        """Shutdown the player"""
        self.stop()
        self._stop_position_thread = True
        if self._position_thread:
            self._position_thread.join(timeout=1.0)
        pygame.mixer.quit()


# Global player instance
player = AudioPlayer()
