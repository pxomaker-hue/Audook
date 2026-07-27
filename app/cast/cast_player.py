"""
Chromecast/Google Home audio output for Audook.

Implements the same interface as app.player.vlc_player.VLCPlayer (play,
pause, resume, stop, seek, next/previous chapter, position/duration
getters, callbacks) so app/player/output_router.py can swap between the two
without PlayerService (app/services/player_service.py) needing to know or
care which one is actually driving playback. EQ/loudness/compression/speed
have no Chromecast equivalent - those methods are no-ops here (VLC-only
audio processing, not applicable once audio is decoded on the cast device).
"""

import re
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from urllib.parse import quote

import pychromecast

from app.models import Audiobook
from app.utils import logger, get_lan_ip

# Same Windows-drive-path detection as vlc_player.py (a "C:\..." style path
# isn't a URL scheme, it just looks like one).
WINDOWS_DRIVE_PATH = re.compile(r'^[a-zA-Z]:[\\/]')

CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
}

DISCOVERY_TIMEOUT = 5.0


def discover_devices() -> List[Dict[str, str]]:
    """Scan the local network for Chromecast/Google Home devices. Blocking,
    with a short timeout - meant to be called on-demand from a "scan"
    action in the UI, not on a hot path."""
    devices = []
    browser = None
    try:
        chromecasts, browser = pychromecast.get_chromecasts(timeout=DISCOVERY_TIMEOUT)
        for cc in chromecasts:
            devices.append({
                "name": cc.name,
                "model": cc.model_name,
                "uuid": str(cc.uuid),
            })
    except Exception as e:
        logger.warning(f"Chromecast discovery failed: {e}")
    finally:
        if browser:
            try:
                pychromecast.discovery.stop_discovery(browser)
            except Exception:
                pass
    return devices


class CastPlayer:
    """Casts audio to a connected Chromecast/Google Home device, mirroring
    VLCPlayer's public interface."""

    def __init__(self):
        self._cast: Optional[pychromecast.Chromecast] = None
        self._device_name: Optional[str] = None
        self._current_audiobook: Optional[Audiobook] = None
        self._current_chapter: Optional[Dict[str, Any]] = None
        self._current_chapter_index: int = 0
        self._position: float = 0.0
        self._duration: float = 0.0
        self._on_position_change: Optional[Callable[[float], None]] = None
        self._on_playback_end: Optional[Callable] = None
        self._stop_update_thread = True
        self._update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._ended_notified = False

    # --- Connection management (not part of VLCPlayer's interface - called
    # directly by PlayerService when the user picks/leaves a cast device) ---

    def connect(self, device_name: str) -> bool:
        try:
            chromecasts, browser = pychromecast.get_chromecasts(timeout=DISCOVERY_TIMEOUT)
            try:
                match = next((cc for cc in chromecasts if cc.name == device_name), None)
                if not match:
                    logger.error(f"Chromecast device not found: {device_name}")
                    return False
                match.wait(timeout=10)
                self._cast = match
                self._device_name = device_name
                self._start_update_thread()
                logger.info(f"Connected to Chromecast: {device_name}")
                return True
            finally:
                pychromecast.discovery.stop_discovery(browser)
        except Exception as e:
            logger.error(f"Failed to connect to Chromecast '{device_name}': {e}")
            return False

    def disconnect(self):
        self._stop_update_thread = True
        if self._cast:
            try:
                self._cast.media_controller.stop()
                self._cast.disconnect(timeout=5)
            except Exception as e:
                logger.warning(f"Error disconnecting Chromecast: {e}")
        self._cast = None
        self._device_name = None
        self._current_audiobook = None
        self._current_chapter = None

    @property
    def is_connected(self) -> bool:
        return self._cast is not None

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name

    # --- VLCPlayer-compatible interface ---

    def play(self, audiobook: Audiobook, chapter: Dict[str, Any], start_position: float = 0.0) -> bool:
        if not self._cast:
            logger.error("No Chromecast connected")
            return False
        if not audiobook or not chapter:
            return False

        audio_file = chapter.get("audio_file", "")
        if not audio_file:
            return False

        media_url = self._resolve_media_url(audio_file)
        content_type = self._guess_content_type(audio_file)

        with self._lock:
            self._current_audiobook = audiobook
            self._current_chapter = chapter
            self._current_chapter_index = chapter.get("index", 0)
            self._position = start_position
            self._duration = chapter.get("duration", 0.0) or 0.0
            self._ended_notified = False

        try:
            mc = self._cast.media_controller
            mc.play_media(
                media_url,
                content_type,
                title=chapter.get("title") or audiobook.title,
                current_time=start_position or None,
                autoplay=True,
                stream_type="BUFFERED",
                metadata={"metadataType": 3, "subtitle": audiobook.title}  # 3 = MusicTrackMediaMetadata
            )
            mc.block_until_active(timeout=10)
            logger.info(f"Casting: {audiobook.title} - {chapter.get('title')} -> {self._device_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to cast media: {e}")
            return False

    def _resolve_media_url(self, audio_file: str) -> str:
        """Chromecast is a separate device on the LAN - it can fetch an
        http(s) URL directly (e.g. an Audiobookshelf/Plex stream), but has
        no notion of a Windows filesystem path, so local files are routed
        through our own backend's streaming endpoint instead."""
        if audio_file.startswith("http://") or audio_file.startswith("https://"):
            return audio_file
        if WINDOWS_DRIVE_PATH.match(audio_file) or Path(audio_file).exists():
            lan_ip = get_lan_ip()
            return f"http://{lan_ip}:5000/api/cast/local-audio?path={quote(audio_file, safe='')}"
        return audio_file

    @staticmethod
    def _guess_content_type(audio_file: str) -> str:
        ext = Path(audio_file.split("?")[0]).suffix.lower()
        return CONTENT_TYPES.get(ext, "audio/mpeg")

    def pause(self) -> bool:
        if not self._cast:
            return False
        try:
            self._cast.media_controller.pause()
            return True
        except Exception as e:
            logger.error(f"Failed to pause cast: {e}")
            return False

    def resume(self) -> bool:
        if not self._cast:
            return False
        try:
            self._cast.media_controller.play()
            return True
        except Exception as e:
            logger.error(f"Failed to resume cast: {e}")
            return False

    def stop(self) -> bool:
        if not self._cast:
            return False
        try:
            self._cast.media_controller.stop()
            self._current_audiobook = None
            self._current_chapter = None
            return True
        except Exception as e:
            logger.error(f"Failed to stop cast: {e}")
            return False

    def seek(self, position: float) -> bool:
        if not self._cast:
            return False
        try:
            self._cast.media_controller.seek(position)
            self._position = position
            return True
        except Exception as e:
            logger.error(f"Failed to seek cast: {e}")
            return False

    def seek_relative(self, seconds: float) -> bool:
        return self.seek(max(0.0, self._position + seconds))

    def set_volume(self, volume: float) -> bool:
        """volume: 0-100, matching VLCPlayer's scale - Chromecast wants 0-1."""
        if not self._cast:
            return False
        try:
            self._cast.set_volume(max(0.0, min(1.0, volume / 100.0)))
            return True
        except Exception as e:
            logger.error(f"Failed to set cast volume: {e}")
            return False

    # No Chromecast equivalent - VLC-only audio processing.
    def set_speed(self, speed: float) -> bool:
        return False

    def set_equalizer(self, bands: Optional[list], preamp: float = 0.0) -> bool:
        return False

    def get_equalizer(self) -> tuple:
        return (None, 0.0)

    def set_loudness_gain(self, gain_db: float) -> bool:
        return False

    def set_compression(self, preset: Optional[str]) -> bool:
        return False

    def get_compression(self) -> Optional[str]:
        return None

    def next_chapter(self) -> bool:
        if not self._current_audiobook:
            return False
        chapters = self._current_audiobook.chapters
        if not chapters or self._current_chapter_index >= len(chapters) - 1:
            return False
        next_index = self._current_chapter_index + 1
        return self.play(self._current_audiobook, chapters[next_index], 0.0)

    def previous_chapter(self) -> bool:
        if not self._current_audiobook:
            return False
        chapters = self._current_audiobook.chapters
        if not chapters or self._current_chapter_index <= 0:
            return False
        prev_index = self._current_chapter_index - 1
        return self.play(self._current_audiobook, chapters[prev_index], 0.0)

    def get_position(self) -> float:
        return self._position

    def get_duration(self) -> float:
        return self._duration

    def get_volume(self) -> float:
        if self._cast and self._cast.status:
            return self._cast.status.volume_level * 100.0
        return 100.0

    def get_speed(self) -> float:
        return 1.0

    def is_playing(self) -> bool:
        if not self._cast:
            return False
        status = self._cast.media_controller.status
        return bool(status and status.player_is_playing)

    def is_paused(self) -> bool:
        if not self._cast:
            return False
        status = self._cast.media_controller.status
        return bool(status and status.player_is_paused)

    def on_position_change(self, callback: Callable[[float], None]):
        self._on_position_change = callback

    def on_playback_end(self, callback: Callable):
        self._on_playback_end = callback

    # --- Position polling (mirrors VLCPlayer._position_update_loop - a
    # Chromecast doesn't push continuous position updates, so this polls
    # its status instead) ---

    def _start_update_thread(self):
        self._stop_update_thread = False
        self._update_thread = threading.Thread(target=self._position_update_loop, daemon=True)
        self._update_thread.start()

    def _position_update_loop(self):
        while not self._stop_update_thread:
            try:
                if self._cast:
                    status = self._cast.media_controller.status
                    if status and status.player_is_playing:
                        self._position = status.adjusted_current_time or status.current_time or self._position
                        self._duration = status.duration or self._duration
                        self._ended_notified = False
                        if self._on_position_change:
                            try:
                                self._on_position_change(self._position)
                            except Exception as e:
                                logger.error(f"Cast position callback error: {e}")
                    elif status and status.player_is_idle and status.idle_reason == "FINISHED" and not self._ended_notified:
                        self._ended_notified = True
                        if self._on_playback_end:
                            try:
                                self._on_playback_end()
                            except Exception as e:
                                logger.error(f"Cast playback end callback error: {e}")
            except Exception as e:
                logger.error(f"Error updating cast position: {e}")

            time.sleep(1.0)


cast_player = CastPlayer()
