"""
Routes playback calls to whichever output is currently active - the local
VLC player, or a connected Chromecast. PlayerService (app/services/
player_service.py) imports `active_output` as if it were the plain VLC
`player` singleton it used to call directly; every method it uses already
exists identically on both backends (see app.cast.cast_player.CastPlayer),
so nothing else about PlayerService needs to change when the output switches.
"""

from typing import Optional, Callable, Dict, Any

from app.player.vlc_player import player as vlc_player
from app.cast.cast_player import cast_player
from app.models import Audiobook


class OutputRouter:
    def __init__(self):
        self._mode = "local"
        # Remembered so they can be re-applied to whichever backend becomes
        # active - each backend only knows about the callbacks registered on
        # itself, and switching output mid-book must not silently drop
        # position-update/chapter-end handling.
        self._on_position_change_cb: Optional[Callable[[float], None]] = None
        self._on_playback_end_cb: Optional[Callable] = None

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def backend(self):
        return cast_player if self._mode == "cast" else vlc_player

    def set_active(self, mode: str):
        """mode: 'local' or 'cast'. Re-applies any previously registered
        callbacks to the newly active backend."""
        self._mode = mode
        if self._on_position_change_cb:
            self.backend.on_position_change(self._on_position_change_cb)
        if self._on_playback_end_cb:
            self.backend.on_playback_end(self._on_playback_end_cb)

    def is_casting(self) -> bool:
        return self._mode == "cast"

    # --- Forwarded to whichever backend is active ---

    def play(self, audiobook: Audiobook, chapter: Dict[str, Any], start_position: float = 0.0) -> bool:
        return self.backend.play(audiobook, chapter, start_position)

    def pause(self) -> bool:
        return self.backend.pause()

    def resume(self) -> bool:
        return self.backend.resume()

    def stop(self) -> bool:
        return self.backend.stop()

    def seek(self, position: float) -> bool:
        return self.backend.seek(position)

    def seek_relative(self, seconds: float) -> bool:
        return self.backend.seek_relative(seconds)

    def set_volume(self, volume: float) -> bool:
        return self.backend.set_volume(volume)

    def set_speed(self, speed: float) -> bool:
        return self.backend.set_speed(speed)

    def set_equalizer(self, bands, preamp: float = 0.0) -> bool:
        return self.backend.set_equalizer(bands, preamp)

    def get_equalizer(self) -> tuple:
        return self.backend.get_equalizer()

    def set_loudness_gain(self, gain_db: float) -> bool:
        return self.backend.set_loudness_gain(gain_db)

    def set_compression(self, preset) -> bool:
        return self.backend.set_compression(preset)

    def get_compression(self):
        return self.backend.get_compression()

    def next_chapter(self) -> bool:
        return self.backend.next_chapter()

    def previous_chapter(self) -> bool:
        return self.backend.previous_chapter()

    def get_position(self) -> float:
        return self.backend.get_position()

    def get_duration(self) -> float:
        return self.backend.get_duration()

    def get_volume(self) -> float:
        return self.backend.get_volume()

    def get_speed(self) -> float:
        return self.backend.get_speed()

    def is_playing(self) -> bool:
        return self.backend.is_playing()

    def is_paused(self) -> bool:
        return self.backend.is_paused()

    def on_position_change(self, callback: Callable[[float], None]):
        self._on_position_change_cb = callback
        self.backend.on_position_change(callback)

    def on_playback_end(self, callback: Callable):
        self._on_playback_end_cb = callback
        self.backend.on_playback_end(callback)


active_output = OutputRouter()
