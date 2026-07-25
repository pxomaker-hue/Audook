"""
Audio player for Audook
Handles audio playback with pygame
"""

import pygame
import pygame.mixer
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path
import threading
import time
import queue
from datetime import datetime

from app.models import Audiobook, Chapter, PlaybackState
from app.utils import logger, format_duration
from app.utils.config_manager import config_manager


class AudioPlayer:
    """Audio player using pygame"""
    
    def __init__(self):
        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.set_num_channels(1)
        
        self._current_audiobook: Optional[Audiobook] = None
        self._current_chapter: Optional[Dict[str, Any]] = None
        self._current_position: float = 0.0
        self._is_playing: bool = False
        self._volume: float = 0.8
        self._speed: float = 1.0
        self._paused: bool = False
        
        # Callbacks
        self._on_playback_start: Optional[Callable] = None
        self._on_playback_pause: Optional[Callable] = None
        self._on_playback_resume: Optional[Callable] = None
        self._on_playback_stop: Optional[Callable] = None
        self._on_position_change: Optional[Callable[[float], None]] = None
        self._on_chapter_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_playback_end: Optional[Callable] = None
        
        # Thread for position updates
        self._position_thread: Optional[threading.Thread] = None
        self._stop_position_thread: bool = False
        self._position_queue = queue.Queue()
        
        # Playback timer
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
            if self._is_playing and not self._paused:
                # Update position based on elapsed time
                elapsed = time.time() - self._last_position_update
                if elapsed > 0:
                    self._current_position += elapsed * self._speed
                
                # Clamp position to chapter duration
                if self._current_chapter:
                    chapter_duration = self._current_chapter.get("duration", 0)
                    if self._current_position > chapter_duration:
                        self._current_position = chapter_duration
                        self._handle_playback_end()
                
                # Notify position change
                if self._on_position_change:
                    try:
                        self._on_position_change(self._current_position)
                    except Exception as e:
                        logger.error(f"Position callback error: {e}")
                
                # Save state periodically
                if self._current_audiobook and self._current_chapter:
                    self._save_playback_state()
                
                self._last_position_update = time.time()
            
            time.sleep(0.1)
    
    def _save_playback_state(self):
        """Save current playback state"""
        if not self._current_audiobook or not self._current_chapter:
            return
        
        state = PlaybackState(
            book_id=self._current_audiobook.id,
            library_id=self._current_audiobook.library_id,
            chapter_id=self._current_chapter.get("id"),
            position=self._current_position,
            is_playing=self._is_playing and not self._paused,
            speed=self._speed,
            last_updated=datetime.now()
        )
        config_manager.update_playback_state(state)
    
    def _load_playback_state(self, audiobook: Audiobook, chapter: Dict[str, Any]) -> float:
        """Load saved playback state for a book/chapter"""
        if config_manager.playback_state:
            if (config_manager.playback_state.book_id == audiobook.id and 
                config_manager.playback_state.library_id == audiobook.library_id):
                return config_manager.playback_state.position
        return 0.0
    
    def play(self, audiobook: Audiobook, chapter: Dict[str, Any], start_position: float = 0.0):
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
        
        # Clamp position to chapter duration
        chapter_duration = chapter.get("duration", 0)
        if self._current_position >= chapter_duration:
            self._current_position = 0.0
        
        # Try to play
        try:
            # Check if we have a local file
            if audiobook.local_path and audiobook.local_path.exists():
                audio_file = str(audiobook.local_path)
            else:
                # For now, we'll use a placeholder
                # In production, this would stream from the server
                logger.warning("Streaming not implemented yet, using placeholder")
                # Create a temporary audio file for testing
                self._create_test_audio()
                audio_file = str(Path("test_audio.wav"))
            
            # Load and play the audio
            try:
                sound = pygame.mixer.Sound(audio_file)
                self._current_sound = sound
                
                # Set volume
                sound.set_volume(self._volume)
                
                # Start playback
                sound.play()
                self._is_playing = True
                self._paused = False
                self._last_position_update = time.time()
                
                # Notify start
                if self._on_playback_start:
                    self._on_playback_start()
                
                return True
            except Exception as e:
                logger.error(f"Failed to play audio: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Playback error: {e}")
            return False
    
    def _create_test_audio(self):
        """Create a test audio file for development"""
        import numpy as np
        import wave
        
        sample_rate = 44100
        duration = 60  # 1 minute
        frequency = 440  # A4 note
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.5
        
        # Convert to 16-bit PCM
        wave_data = (wave_data * 32767).astype(np.int16)
        
        # Save as WAV file
        with wave.open("test_audio.wav", "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(wave_data.tobytes())
    
    def pause(self):
        """Pause playback"""
        if not self._is_playing or self._paused:
            return
        
        pygame.mixer.pause()
        self._paused = True
        
        if self._on_playback_pause:
            self._on_playback_pause()
    
    def resume(self):
        """Resume playback"""
        if not self._is_playing or not self._paused:
            return
        
        pygame.mixer.unpause()
        self._paused = False
        self._last_position_update = time.time()
        
        if self._on_playback_resume:
            self._on_playback_resume()
    
    def stop(self):
        """Stop playback"""
        if self._is_playing:
            pygame.mixer.stop()
            self._is_playing = False
            self._paused = False
        
        if self._on_playback_stop:
            self._on_playback_stop()
        
        self._current_audiobook = None
        self._current_chapter = None
        self._current_position = 0.0
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self._is_playing and not self._paused:
            self.pause()
        else:
            if not self._is_playing:
                # If we have a current audiobook, resume from current position
                if self._current_audiobook and self._current_chapter:
                    self.play(self._current_audiobook, self._current_chapter, self._current_position)
            else:
                self.resume()
    
    def seek(self, position: float):
        """Seek to a specific position in seconds"""
        if not self._is_playing or not self._current_chapter:
            return
        
        chapter_duration = self._current_chapter.get("duration", 0)
        position = max(0, min(position, chapter_duration))
        
        # For pygame, we need to stop and restart at new position
        # This is a limitation of pygame.mixer
        self._current_position = position
        
        # Stop current playback
        self.stop()
        
        # Restart at new position
        if self._current_audiobook and self._current_chapter:
            self.play(self._current_audiobook, self._current_chapter, position)
    
    def seek_relative(self, delta: float):
        """Seek relative to current position"""
        if not self._is_playing:
            return
        
        new_position = self._current_position + delta
        self.seek(new_position)
    
    def next_chapter(self):
        """Play next chapter"""
        if not self._current_audiobook or not self._current_chapter:
            return False
        
        current_index = self._current_chapter.get("index", 0)
        chapters = self._current_audiobook.chapters
        
        if current_index + 1 < len(chapters):
            next_chap = chapters[current_index + 1]
            return self.play(self._current_audiobook, next_chap, 0.0)
        
        return False
    
    def previous_chapter(self):
        """Play previous chapter"""
        if not self._current_audiobook or not self._current_chapter:
            return False
        
        current_index = self._current_chapter.get("index", 0)
        chapters = self._current_audiobook.chapters
        
        if current_index - 1 >= 0:
            prev_chap = chapters[current_index - 1]
            # Start from the beginning of previous chapter
            return self.play(self._current_audiobook, prev_chap, 0.0)
        
        return False
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        volume = max(0.0, min(1.0, volume))
        self._volume = volume
        
        if hasattr(self, '_current_sound') and self._current_sound:
            self._current_sound.set_volume(volume)
        
        config_manager.config.volume = volume
        config_manager.save_config()
    
    def set_speed(self, speed: float):
        """Set playback speed (0.5 to 2.0)"""
        speed = max(0.5, min(2.0, speed))
        self._speed = speed
        
        config_manager.config.playback_speed = speed
        config_manager.save_config()
    
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
        """Check if currently paused"""
        return self._paused
    
    def get_current_position(self) -> float:
        """Get current playback position in seconds"""
        return self._current_position
    
    def get_current_duration(self) -> float:
        """Get current chapter duration in seconds"""
        if self._current_chapter:
            return self._current_chapter.get("duration", 0)
        return 0.0
    
    def get_current_audiobook(self) -> Optional[Audiobook]:
        """Get current audiobook"""
        return self._current_audiobook
    
    def get_current_chapter(self) -> Optional[Dict[str, Any]]:
        """Get current chapter"""
        return self._current_chapter
    
    def get_progress_percent(self) -> float:
        """Get current progress as percentage"""
        duration = self.get_current_duration()
        if duration <= 0:
            return 0.0
        return (self._current_position / duration) * 100
    
    def get_time_remaining(self) -> float:
        """Get remaining time in current chapter"""
        duration = self.get_current_duration()
        return max(0, duration - self._current_position)
    
    def _handle_playback_end(self):
        """Handle end of playback"""
        if self._on_playback_end:
            self._on_playback_end()
        
        # Auto-play next chapter
        self.next_chapter()
    
    # Callback setters
    def on_playback_start(self, callback: Callable):
        self._on_playback_start = callback
    
    def on_playback_pause(self, callback: Callable):
        self._on_playback_pause = callback
    
    def on_playback_resume(self, callback: Callable):
        self._on_playback_resume = callback
    
    def on_playback_stop(self, callback: Callable):
        self._on_playback_stop = callback
    
    def on_position_change(self, callback: Callable[[float], None]):
        self._on_position_change = callback
    
    def on_chapter_change(self, callback: Callable[[Dict[str, Any]], None]):
        self._on_chapter_change = callback
    
    def on_playback_end(self, callback: Callable):
        self._on_playback_end = callback
    
    def cleanup(self):
        """Cleanup resources"""
        self._stop_position_thread = True
        if self._position_thread:
            self._position_thread.join(timeout=1.0)
        
        self.stop()
        pygame.mixer.quit()


# Global player instance
player = AudioPlayer()
