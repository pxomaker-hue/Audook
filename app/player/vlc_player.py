"""
VLC-based audio player for Audook
Supports streaming from Plex, Audiobookshelf, and local files
"""

import vlc
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import threading
import time
from datetime import datetime

from app.models import Audiobook
from app.utils import logger, format_duration


class VLCPlayer:
    """Audio player using VLC library for streaming support"""

    def __init__(self):
        """Initialize VLC player"""
        self.instance = vlc.Instance()
        self.player = self.instance.media_list_player_new()
        self.media_list = self.instance.media_list_new()

        self._current_audiobook: Optional[Audiobook] = None
        self._current_chapter: Optional[Dict[str, Any]] = None
        self._current_chapter_index: int = 0
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._volume: float = 80  # 0-100
        self._speed: float = 1.0  # 0.5-2.0

        # Position tracking
        self._position: float = 0.0
        self._duration: float = 0.0
        self._last_position_update: float = 0.0

        # Callbacks
        self._on_playback_start: Optional[Callable] = None
        self._on_playback_pause: Optional[Callable] = None
        self._on_playback_resume: Optional[Callable] = None
        self._on_playback_stop: Optional[Callable] = None
        self._on_position_change: Optional[Callable[[float], None]] = None
        self._on_chapter_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_playback_end: Optional[Callable] = None

        # Position update thread
        self._update_thread: Optional[threading.Thread] = None
        self._stop_update_thread: bool = False

        self._start_position_thread()

    def _start_position_thread(self):
        """Start thread for position updates"""
        self._stop_update_thread = False
        self._update_thread = threading.Thread(target=self._position_update_loop, daemon=True)
        self._update_thread.start()

    def _position_update_loop(self):
        """Continuously update position while playing"""
        while not self._stop_update_thread:
            if self._is_playing and not self._is_paused and self.player.is_playing():
                try:
                    # Get current position from VLC
                    media = self.player.get_media_list()
                    if media and media.count() > 0:
                        current_media = self.player.get_media()
                        if current_media:
                            # Position in milliseconds
                            position_ms = current_media.get_duration()
                            if position_ms > 0:
                                # Calculate actual position
                                player_pos = self.player.get_media_player().get_time()
                                if player_pos >= 0:
                                    self._position = player_pos / 1000.0  # Convert to seconds
                                    self._duration = position_ms / 1000.0

                                    # Notify position change
                                    if self._on_position_change:
                                        try:
                                            self._on_position_change(self._position)
                                        except Exception as e:
                                            logger.error(f"Position callback error: {e}")

                except Exception as e:
                    logger.error(f"Error updating position: {e}")

            time.sleep(0.5)

    def play(self, audiobook: Audiobook, chapter: Dict[str, Any], start_position: float = 0.0) -> bool:
        """Play an audiobook chapter"""
        try:
            if not audiobook or not chapter:
                logger.warning("No audiobook or chapter to play")
                return False

            self._current_audiobook = audiobook
            self._current_chapter = chapter
            self._current_chapter_index = chapter.get("index", 0)
            self._position = start_position

            # Get audio file/URL
            audio_file = chapter.get("audio_file", "")
            if not audio_file:
                logger.error("No audio file path in chapter")
                return False

            # Create VLC media
            media = self.instance.media_new(audio_file)
            if not media:
                logger.error(f"Failed to create VLC media: {audio_file}")
                return False

            # Clear current playlist and add new media
            self.media_list = self.instance.media_list_new()
            self.media_list.add_media(media)
            self.player.set_media_list(self.media_list)

            # Set volume and speed
            self.player.get_media_player().audio_set_volume(self._volume)

            # Start playback
            self.player.play()
            self._is_playing = True
            self._is_paused = False
            self._last_position_update = time.time()

            logger.info(f"Playing: {audiobook.title} - {chapter.get('title')}")

            # Seek to start position if specified
            if start_position > 0:
                self.player.get_media_player().set_time(int(start_position * 1000))

            # Notify callbacks
            if self._on_playback_start:
                try:
                    self._on_playback_start()
                except Exception as e:
                    logger.error(f"Playback start callback error: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return False

    def pause(self) -> bool:
        """Pause playback"""
        try:
            if self._is_playing and not self._is_paused:
                self.player.pause()
                self._is_paused = True

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
        try:
            if self._is_playing and self._is_paused:
                self.player.pause()
                self._is_paused = False
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
        try:
            if self._is_playing:
                self.player.stop()
                self._is_playing = False
                self._is_paused = False
                self.media_list = self.instance.media_list_new()

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
        """Seek to position in seconds"""
        try:
            if self._is_playing:
                # Clamp position to valid range
                position = max(0.0, min(position, self._duration))
                self.player.get_media_player().set_time(int(position * 1000))
                self._position = position
                return True
        except Exception as e:
            logger.error(f"Seek error: {e}")

        return False

    def seek_relative(self, seconds: float) -> bool:
        """Seek relative to current position"""
        new_position = self._position + seconds
        return self.seek(new_position)

    def set_volume(self, volume: float) -> bool:
        """Set volume (0-100)"""
        try:
            self._volume = max(0, min(100, int(volume)))
            self.player.get_media_player().audio_set_volume(self._volume)
            return True
        except Exception as e:
            logger.error(f"Set volume error: {e}")
            return False

    def set_speed(self, speed: float) -> bool:
        """Set playback speed (0.5-2.0)"""
        try:
            # VLC speed is rate (1.0 = normal, 2.0 = 2x, 0.5 = 0.5x)
            speed = max(0.5, min(2.0, speed))
            self._speed = speed
            self.player.get_media_player().set_rate(speed)
            return True
        except Exception as e:
            logger.error(f"Set speed error: {e}")
            return False

    def next_chapter(self) -> bool:
        """Play next chapter"""
        if not self._current_audiobook:
            return False

        chapters = self._current_audiobook.chapters
        if not chapters or self._current_chapter_index >= len(chapters) - 1:
            return False

        next_index = self._current_chapter_index + 1
        next_chapter = chapters[next_index]
        return self.play(self._current_audiobook, next_chapter, 0.0)

    def previous_chapter(self) -> bool:
        """Play previous chapter"""
        if not self._current_audiobook:
            return False

        chapters = self._current_audiobook.chapters
        if not chapters or self._current_chapter_index <= 0:
            return False

        prev_index = self._current_chapter_index - 1
        prev_chapter = chapters[prev_index]
        return self.play(self._current_audiobook, prev_chapter, 0.0)

    # Getters

    def get_position(self) -> float:
        """Get current position in seconds"""
        return self._position

    def get_duration(self) -> float:
        """Get chapter duration in seconds"""
        return self._duration

    def get_volume(self) -> float:
        """Get volume (0-100)"""
        return self._volume

    def get_speed(self) -> float:
        """Get playback speed"""
        return self._speed

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self._is_playing and not self._is_paused

    def is_paused(self) -> bool:
        """Check if paused"""
        return self._is_paused

    def get_current_audiobook(self) -> Optional[Audiobook]:
        """Get current audiobook"""
        return self._current_audiobook

    def get_current_chapter(self) -> Optional[Dict[str, Any]]:
        """Get current chapter"""
        return self._current_chapter

    # Callbacks

    def on_playback_start(self, callback: Callable):
        """Set callback for playback start"""
        self._on_playback_start = callback

    def on_playback_pause(self, callback: Callable):
        """Set callback for playback pause"""
        self._on_playback_pause = callback

    def on_playback_resume(self, callback: Callable):
        """Set callback for playback resume"""
        self._on_playback_resume = callback

    def on_playback_stop(self, callback: Callable):
        """Set callback for playback stop"""
        self._on_playback_stop = callback

    def on_position_change(self, callback: Callable[[float], None]):
        """Set callback for position change"""
        self._on_position_change = callback

    def on_chapter_change(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for chapter change"""
        self._on_chapter_change = callback

    def on_playback_end(self, callback: Callable):
        """Set callback for playback end"""
        self._on_playback_end = callback

    def shutdown(self):
        """Shutdown player"""
        self.stop()
        self._stop_update_thread = True
        if self._update_thread:
            self._update_thread.join(timeout=2.0)
        logger.info("VLC Player shutdown")


# Global player instance
player = VLCPlayer()
