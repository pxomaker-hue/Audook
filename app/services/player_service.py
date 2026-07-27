"""
Player service - manages playback and progress
"""

import threading
import time
from typing import Optional, Callable
from app.player import player, progress_manager
from app.models import Audiobook
from app.utils import logger
from app.sync import progress_sync
from app.database import get_session, AppSettingsRepository, EqualizerPresetRepository, BookRepository
from app.utils import audio_loudness

# Consider the current chapter "fully listened" (for auto mark-as-finished)
# once we're this close to the end of the last chapter.
AUTO_FINISH_THRESHOLD_SECONDS = 2.0

# How long the sleep timer's volume fade-out takes, at the very end of the
# countdown, before actually pausing playback.
SLEEP_TIMER_FADE_SECONDS = 20


class PlayerService:
    """Service for managing audio playback"""

    def __init__(self):
        self.current_audiobook: Optional[Audiobook] = None
        self.current_chapter_index: int = 0
        self._on_position_changed: Optional[Callable] = None
        self._auto_finished: bool = False
        self.equalizer_preset_id: Optional[str] = None
        self.loudness_normalization_enabled: bool = False
        self.compression_preset: Optional[str] = None
        self._sleep_timer_end_time: Optional[float] = None
        self._sleep_timer_generation: int = 0

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
                cleaned_path = self._get_cleaned_chapter_path(audiobook.id, chapter_idx)
                if cleaned_path:
                    chapter = {**chapter, "audio_file": cleaned_path}
                success = player.play(audiobook, chapter, position)

                if success:
                    logger.info(f"Started playing: {audiobook.title}")
                    self._apply_loudness_gain_for_current_book()
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
            self.cancel_sleep_timer()
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

    def set_sleep_timer(self, minutes: Optional[float]) -> bool:
        """Start (or restart) a sleep timer: fades the volume out over the
        last SLEEP_TIMER_FADE_SECONDS then pauses. Passing None/0 cancels
        any running timer without touching playback."""
        self._sleep_timer_generation += 1
        generation = self._sleep_timer_generation

        if not minutes or minutes <= 0:
            self._sleep_timer_end_time = None
            return True

        self._sleep_timer_end_time = time.time() + minutes * 60
        thread = threading.Thread(target=self._sleep_timer_loop, args=(generation,), daemon=True)
        thread.start()
        return True

    def cancel_sleep_timer(self):
        self.set_sleep_timer(None)

    def get_sleep_timer_remaining_seconds(self) -> Optional[float]:
        if self._sleep_timer_end_time is None:
            return None
        return max(0.0, self._sleep_timer_end_time - time.time())

    def _sleep_timer_loop(self, generation: int):
        try:
            while generation == self._sleep_timer_generation:
                remaining = self.get_sleep_timer_remaining_seconds()
                if remaining is None:
                    return
                if remaining <= SLEEP_TIMER_FADE_SECONDS:
                    break
                time.sleep(1)

            if generation != self._sleep_timer_generation:
                return

            self._fade_out_and_pause(generation)
        except Exception as e:
            logger.error(f"Sleep timer error: {e}")
        finally:
            if generation == self._sleep_timer_generation:
                self._sleep_timer_end_time = None

    def _fade_out_and_pause(self, generation: int):
        """Ramp the volume down to 0 over SLEEP_TIMER_FADE_SECONDS, pause,
        then restore the original volume so the next resume isn't silent.
        Aborts (without touching volume) if the timer was cancelled/reset
        mid-fade, i.e. a newer generation has since started."""
        original_volume = self.get_volume()
        steps = 20
        step_duration = SLEEP_TIMER_FADE_SECONDS / steps

        for i in range(steps, -1, -1):
            if generation != self._sleep_timer_generation:
                return
            self.set_volume(original_volume * i / steps)
            time.sleep(step_duration)

        if generation != self._sleep_timer_generation:
            return

        self.pause()
        self.set_volume(original_volume)
        logger.info("Sleep timer elapsed - playback paused")

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

    def set_equalizer_preset(self, preset_id: Optional[str], bands: Optional[list] = None,
                              preamp: float = 0.0) -> bool:
        """Apply an equalizer preset (preset_id=None disables it) and
        remember the choice for next launch."""
        try:
            if not player.set_equalizer(bands, preamp):
                return False
            self.equalizer_preset_id = preset_id
            self._save_setting('equalizer_preset_id', preset_id or '')
            return True
        except Exception as e:
            logger.error(f"Failed to set equalizer preset: {e}")
            return False

    def cycle_equalizer_preset(self) -> Optional[str]:
        """Switch to the next equalizer preset in the list (off -> preset 1
        -> preset 2 -> ... -> off), for the player button. Returns the new
        preset_id (None if it landed back on "off")."""
        session = get_session()
        try:
            presets = EqualizerPresetRepository(session).get_all()
            # Cycle order: off, then every preset in position order
            ids = [None] + [p.id for p in presets]
            try:
                current_index = ids.index(self.equalizer_preset_id)
            except ValueError:
                current_index = 0
            next_id = ids[(current_index + 1) % len(ids)]

            if next_id is None:
                self.set_equalizer_preset(None)
            else:
                preset = next((p for p in presets if p.id == next_id), None)
                if preset:
                    self.set_equalizer_preset(preset.id, preset.bands, preset.preamp)
            return self.equalizer_preset_id
        finally:
            session.close()

    COMPRESSION_STEPS = [None, 'leger', 'modere', 'fort']

    def cycle_compression(self) -> Optional[str]:
        """Switch to the next compression preset (off -> léger -> modéré ->
        fort -> off), for the "..." menu button. Returns the new preset key
        (None if it landed back on "off")."""
        try:
            current_index = self.COMPRESSION_STEPS.index(self.compression_preset)
        except ValueError:
            current_index = 0
        next_preset = self.COMPRESSION_STEPS[(current_index + 1) % len(self.COMPRESSION_STEPS)]

        if player.set_compression(next_preset):
            self.compression_preset = next_preset
            self._save_setting('compression_preset', next_preset or '')
        return self.compression_preset

    def set_loudness_normalization(self, enabled: bool) -> bool:
        """Toggle per-book EBU-style loudness matching and remember the
        choice for next launch. Applies (or clears) the gain for whatever's
        currently playing immediately."""
        try:
            self.loudness_normalization_enabled = enabled
            self._save_setting('loudness_normalization_enabled', '1' if enabled else '0')
            if enabled:
                self._apply_loudness_gain_for_current_book()
            else:
                player.set_loudness_gain(0.0)
            return True
        except Exception as e:
            logger.error(f"Failed to set loudness normalization: {e}")
            return False

    def _apply_loudness_gain_for_current_book(self):
        """Apply the current book's cached loudness gain if one exists;
        otherwise kick off a one-time background measurement (never blocks
        playback) and apply it once ready. No-op if the feature is off."""
        if not self.loudness_normalization_enabled or not self.current_audiobook:
            return

        book_id = self.current_audiobook.id
        session = get_session()
        try:
            cached_gain = BookRepository(session).get_loudness_gain(book_id)
        finally:
            session.close()

        if cached_gain is not None:
            player.set_loudness_gain(cached_gain)
            return

        player.set_loudness_gain(0.0)
        chapter = self.current_audiobook.chapters[self.current_chapter_index]
        source = chapter.get("audio_file")
        if not source:
            return

        def measure_and_apply():
            gain = audio_loudness.measure_loudness_gain(source)
            if gain is None:
                return
            measure_session = get_session()
            try:
                BookRepository(measure_session).set_loudness_gain(book_id, gain)
            finally:
                measure_session.close()
            # Only apply live if we're still on the same book - avoids
            # slapping a stale gain onto whatever's playing by the time this
            # (potentially slow) measurement finishes.
            if self.current_audiobook and self.current_audiobook.id == book_id:
                player.set_loudness_gain(gain)

        threading.Thread(target=measure_and_apply, daemon=True).start()

    def _get_cleaned_chapter_path(self, book_id: str, chapter_index: int) -> Optional[str]:
        """Local path of a previously-cleaned (noise-reduced) copy of this
        chapter, if one exists - see start_noise_reduction below."""
        session = get_session()
        try:
            return BookRepository(session).get_cleaned_chapter_path(book_id, chapter_index)
        finally:
            session.close()

    def start_noise_reduction(self, book_id: str) -> bool:
        """Kick off a one-time, opt-in noise-reduction pass over every
        chapter of `book_id` (see app/utils/noise_reduction.py), in the
        background - never blocks the caller. Cleaned chapters are used
        automatically on the next play() once ready (see
        _get_cleaned_chapter_path above). Returns False if it's already
        running for this book."""
        from app.services.library_service import LibraryService
        from app.utils import noise_reduction, get_cache_path

        session = get_session()
        try:
            repo = BookRepository(session)
            if repo.get_noise_reduction_status(book_id) == 'processing':
                return False
            repo.set_noise_reduction_status(book_id, 'processing')
        finally:
            session.close()

        def process():
            try:
                audiobook = LibraryService.get_book_by_id(book_id)
                if not audiobook or not audiobook.chapters:
                    raise ValueError("Book not found or has no chapters")

                cleaned_count = 0
                for index, chapter in enumerate(audiobook.chapters):
                    source = chapter.get("audio_file")
                    if not source:
                        continue
                    output_path = get_cache_path(book_id, f"clean_{index}")
                    if noise_reduction.clean_audio_file(source, output_path):
                        cleaned_count += 1
                        clean_session = get_session()
                        try:
                            BookRepository(clean_session).set_cleaned_chapter_path(book_id, index, str(output_path))
                        finally:
                            clean_session.close()

                # Every chapter failed (most commonly: ffmpeg isn't
                # available) - don't report success when nothing was
                # actually cleaned.
                final_status = 'done' if cleaned_count > 0 else 'error'
                done_session = get_session()
                try:
                    BookRepository(done_session).set_noise_reduction_status(book_id, final_status)
                finally:
                    done_session.close()
            except Exception as e:
                logger.error(f"Noise reduction failed for book {book_id}: {e}")
                error_session = get_session()
                try:
                    BookRepository(error_session).set_noise_reduction_status(book_id, 'error')
                finally:
                    error_session.close()

        threading.Thread(target=process, daemon=True).start()
        return True

    def restore_audio_settings(self):
        """Reapply the persisted equalizer/loudness/compression preferences
        at backend startup, before any playback begins."""
        session = get_session()
        try:
            settings_repo = AppSettingsRepository(session)
            preset_id = settings_repo.get('equalizer_preset_id') or None
            loudness_normalization = settings_repo.get('loudness_normalization_enabled') == '1'
            compression_preset = settings_repo.get('compression_preset') or None

            if preset_id:
                preset = EqualizerPresetRepository(session).get_by_id(preset_id)
                if preset:
                    self.set_equalizer_preset(preset.id, preset.bands, preset.preamp)
            self.loudness_normalization_enabled = loudness_normalization
            if compression_preset:
                player.set_compression(compression_preset)
                self.compression_preset = compression_preset
        except Exception as e:
            logger.error(f"Failed to restore audio settings: {e}")
        finally:
            session.close()

    def _save_setting(self, key: str, value: str):
        session = get_session()
        try:
            AppSettingsRepository(session).set(key, value)
        finally:
            session.close()

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

    def get_volume(self) -> float:
        """Get current volume (0-100)"""
        return player.get_volume()

    def get_speed(self) -> float:
        """Get current playback speed"""
        return player.get_speed()

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
