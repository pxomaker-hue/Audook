import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { getApiBase } from '../config';
import { notifyBookmarksChanged } from '../bookmarkEvents';
import { usePolling } from './usePolling';

// Click window (ms) to detect a double-click on the "previous chapter" button
const PREVIOUS_DOUBLE_CLICK_WINDOW = 300;
// Below this many elapsed seconds, a single click on "previous" also jumps to
// the previous chapter instead of just restarting the current one.
const RESTART_THRESHOLD_SECONDS = 2;
const SEEK_STEP_SECONDS = 30;
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
// Sleep timer cycle: null (off) then each duration in minutes, looping.
const SLEEP_TIMER_STEPS: Array<number | null> = [null, 5, 10, 15, 20, 30, 60];

export interface PlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  currentChapterTitle: string | null;
  currentChapterIndex: number | null;
  position: number;
  duration: number;
  volume: number;
  speed: number;
  equalizerPresetId: string | null;
  loudnessNormalizationEnabled: boolean;
  compressionPreset: string | null;
  sleepTimerRemainingSeconds: number | null;
  isCasting: boolean;
  castDeviceName: string | null;
}

export interface CastDevice {
  name: string;
  model: string;
  uuid: string;
}

export interface EqualizerPreset {
  id: string;
  name: string;
  bands: number[];
  preamp: number;
  is_builtin: boolean;
}

export function formatTime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Shared state + controls for the player, used by both the full/compact
// Player (docked in the main window) and the detached mini-player window -
// both drive the same backend transport player, just with different UI.
export function usePlayerState() {
  const [state, setState] = useState<PlayerState>({
    isPlaying: false,
    currentBook: null,
    currentChapterTitle: null,
    currentChapterIndex: null,
    position: 0,
    duration: 0,
    volume: 80,
    speed: 1,
    equalizerPresetId: null,
    loudnessNormalizationEnabled: false,
    compressionPreset: null,
    sleepTimerRemainingSeconds: null,
    isCasting: false,
    castDeviceName: null
  });
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [bookmarkAdded, setBookmarkAdded] = useState(false);
  const [equalizerPresets, setEqualizerPresets] = useState<EqualizerPreset[]>([]);
  const [sleepTimerStepIndex, setSleepTimerStepIndex] = useState(0);
  const [castDevices, setCastDevices] = useState<CastDevice[]>([]);
  const [castScanning, setCastScanning] = useState(false);
  const [castConnecting, setCastConnecting] = useState<string | null>(null);
  const [castError, setCastError] = useState<string | null>(null);
  const previousClickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Bumped whenever the sleep timer is changed from here. A state poll that
  // started before the change but is answered after it carries the OLD timer
  // state - applying it would show the timer as off and reset the step index.
  const sleepTimerEpoch = useRef(0);

  const fetchState = async () => {
    try {
      const epoch = sleepTimerEpoch.current;
      const response = await axios.get(`${getApiBase()}/player/state`);
      if (epoch !== sleepTimerEpoch.current) return; // stale: the next poll (1 s) will be fresh
      // Backend uses snake_case (is_playing); explicitly map it instead of
      // relying on the spread, otherwise `isPlaying` never actually updates.
      setState(prev => {
        const next = {
          ...prev,
          ...response.data,
          isPlaying: response.data.is_playing ?? prev.isPlaying,
          equalizerPresetId: response.data.equalizer_preset_id ?? null,
          loudnessNormalizationEnabled: response.data.loudness_normalization_enabled ?? false,
          compressionPreset: response.data.compression_preset ?? null,
          sleepTimerRemainingSeconds: response.data.sleep_timer_remaining_seconds ?? null,
          isCasting: response.data.is_casting ?? false,
          castDeviceName: response.data.cast_device_name ?? null
        };
        // Same values as last tick (typical while paused): keep the old
        // object so React skips the re-render instead of redoing the whole
        // player every second for nothing.
        const unchanged = (Object.keys(next) as (keyof typeof next)[]).every(
          (k) => k === 'currentBook' ? next.currentBook?.id === prev.currentBook?.id : next[k] === (prev as any)[k]
        );
        return unchanged ? prev : next;
      });
    } catch (error) {
      console.error('Failed to get player state:', error);
    }
  };

  useEffect(() => {
    fetchState();

    const offState = window.electron?.onPlayerState?.((newState: any) => {
      setState(prev => ({ ...prev, ...newState }));
    });

    const offPosition = window.electron?.onPlayerPosition?.((data: any) => {
      setState(prev => ({ ...prev, position: data.position }));
    });

    axios.get(`${getApiBase()}/equalizer/presets`)
      .then(res => setEqualizerPresets(res.data))
      .catch(error => console.error('Failed to load equalizer presets:', error));

    return () => {
      offState?.();
      offPosition?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  usePolling(fetchState, 1000);

  useEffect(() => {
    return () => {
      if (previousClickTimer.current) {
        clearTimeout(previousClickTimer.current);
      }
    };
  }, []);


  // The button's step index is local, so it has to follow the timer's real
  // state: when a running timer ends (or is cancelled elsewhere) the remaining
  // time goes from a number back to null - without resetting here the next
  // click kept cycling from the last chosen duration (10 min -> 15 min)
  // instead of starting over at 5. Only the number -> null transition counts,
  // so a not-yet-updated null right after a click doesn't reset it.
  const previousSleepRemaining = useRef<number | null>(null);
  useEffect(() => {
    if (previousSleepRemaining.current !== null && state.sleepTimerRemainingSeconds === null) {
      setSleepTimerStepIndex(0);
    }
    previousSleepRemaining.current = state.sleepTimerRemainingSeconds;
  }, [state.sleepTimerRemainingSeconds]);

  const handlePlayPause = async () => {
    try {
      if (state.isPlaying) {
        await axios.post(`${getApiBase()}/player/pause`);
      } else {
        await axios.post(`${getApiBase()}/player/resume`);
      }
    } catch (error) {
      console.error('Failed to toggle playback:', error);
    } finally {
      // Re-fetch the real state instead of optimistically flipping a boolean:
      // if playback was started from another page moments ago, our local
      // state can still be stale, which would otherwise send the wrong
      // command (e.g. "resume" on an already-playing book).
      fetchState();
    }
  };

  const goToPreviousChapter = async () => {
    try {
      await axios.post(`${getApiBase()}/player/previous-chapter`);
    } catch (error) {
      console.error('Failed to go to previous chapter:', error);
    }
  };

  const restartChapter = async () => {
    setState(prev => ({ ...prev, position: 0 }));
    try {
      await axios.post(`${getApiBase()}/player/seek`, { position: 0 });
    } catch (error) {
      console.error('Failed to restart chapter:', error);
    }
  };

  const handlePreviousClick = () => {
    if (previousClickTimer.current) {
      // Second click within the window: double-click -> previous chapter,
      // regardless of elapsed time.
      clearTimeout(previousClickTimer.current);
      previousClickTimer.current = null;
      goToPreviousChapter();
      return;
    }

    previousClickTimer.current = setTimeout(() => {
      previousClickTimer.current = null;
      // Single click resolved: restart the current chapter if we're well
      // into it, otherwise just go to the previous one.
      if (state.position > RESTART_THRESHOLD_SECONDS) {
        restartChapter();
      } else {
        goToPreviousChapter();
      }
    }, PREVIOUS_DOUBLE_CLICK_WINDOW);
  };

  const handleNextClick = async () => {
    try {
      await axios.post(`${getApiBase()}/player/next-chapter`);
    } catch (error) {
      console.error('Failed to go to next chapter:', error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    const newPosition = percentage * state.duration;
    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${getApiBase()}/player/seek`, { position: newPosition });
  };

  const handleSeekStep = (deltaSeconds: number) => {
    const newPosition = Math.max(0, Math.min(state.duration, state.position + deltaSeconds));
    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${getApiBase()}/player/seek`, { position: newPosition });
  };

  const handleVolumeChange = (volume: number) => {
    setState(prev => ({ ...prev, volume }));
    axios.post(`${getApiBase()}/player/volume`, { volume });
  };

  const handleAddBookmark = async () => {
    if (!state.currentBook) return;
    try {
      setAddingBookmark(true);
      await axios.post(`${getApiBase()}/books/${state.currentBook.id}/bookmarks`, {});
      notifyBookmarksChanged();
      setBookmarkAdded(true);
      setTimeout(() => setBookmarkAdded(false), 1800);
    } catch (error) {
      console.error('Failed to add bookmark:', error);
    } finally {
      setAddingBookmark(false);
    }
  };

  const handleCycleSpeed = () => {
    const currentIndex = SPEEDS.indexOf(state.speed);
    const nextSpeed = SPEEDS[(currentIndex + 1) % SPEEDS.length] ?? 1;
    setState(prev => ({ ...prev, speed: nextSpeed }));
    axios.post(`${getApiBase()}/player/speed`, { speed: nextSpeed });
  };

  const handleCycleEqualizer = async () => {
    try {
      const response = await axios.post(`${getApiBase()}/player/equalizer/cycle`);
      setState(prev => ({ ...prev, equalizerPresetId: response.data.preset_id ?? null }));
    } catch (error) {
      console.error('Failed to cycle equalizer:', error);
    }
  };

  const handleToggleLoudnessNormalization = async () => {
    const next = !state.loudnessNormalizationEnabled;
    setState(prev => ({ ...prev, loudnessNormalizationEnabled: next }));
    try {
      await axios.post(`${getApiBase()}/player/loudness-normalization`, { enabled: next });
    } catch (error) {
      console.error('Failed to toggle loudness normalization:', error);
      setState(prev => ({ ...prev, loudnessNormalizationEnabled: !next }));
    }
  };

  const handleCycleCompression = async () => {
    try {
      const response = await axios.post(`${getApiBase()}/player/compression/cycle`);
      setState(prev => ({ ...prev, compressionPreset: response.data.preset ?? null }));
    } catch (error) {
      console.error('Failed to cycle compression:', error);
    }
  };

  const handleCycleSleepTimer = async () => {
    const nextIndex = (sleepTimerStepIndex + 1) % SLEEP_TIMER_STEPS.length;
    const minutes = SLEEP_TIMER_STEPS[nextIndex];
    setSleepTimerStepIndex(nextIndex);
    sleepTimerEpoch.current += 1; // polls already in flight are now stale
    try {
      const response = await axios.post(`${getApiBase()}/player/sleep-timer`, { minutes });
      sleepTimerEpoch.current += 1; // ...and so are those started while the POST was running
      setState(prev => ({ ...prev, sleepTimerRemainingSeconds: response.data.sleep_timer_remaining_seconds ?? null }));
    } catch (error) {
      console.error('Failed to set sleep timer:', error);
    }
  };

  const handleScanCastDevices = async () => {
    try {
      setCastError(null);
      setCastScanning(true);
      const response = await axios.get(`${getApiBase()}/cast/devices`);
      setCastDevices(response.data);
    } catch (error) {
      console.error('Failed to scan for cast devices:', error);
    } finally {
      setCastScanning(false);
    }
  };

  const handleConnectCastDevice = async (deviceName: string) => {
    try {
      setCastError(null);
      setCastConnecting(deviceName);
      await axios.post(`${getApiBase()}/cast/connect`, { device_name: deviceName });
      await fetchState();
    } catch (error) {
      console.error('Failed to connect to cast device:', error);
      setCastError("Impossible de se connecter à cet appareil. Réessayez, ou vérifiez qu'il est bien sur le même réseau.");
    } finally {
      setCastConnecting(null);
    }
  };

  const handleDisconnectCastDevice = async () => {
    try {
      await axios.post(`${getApiBase()}/cast/disconnect`);
      await fetchState();
    } catch (error) {
      console.error('Failed to disconnect cast device:', error);
    }
  };

  return {
    state,
    addingBookmark,
    bookmarkAdded,
    equalizerPresets,
    handlePlayPause,
    handlePreviousClick,
    handleNextClick,
    handleSeek,
    handleSeekStep,
    handleVolumeChange,
    handleAddBookmark,
    handleCycleSpeed,
    handleCycleEqualizer,
    handleToggleLoudnessNormalization,
    handleCycleCompression,
    handleCycleSleepTimer,
    castDevices,
    castScanning,
    castConnecting,
    castError,
    handleScanCastDevices,
    handleConnectCastDevice,
    handleDisconnectCastDevice,
    SEEK_STEP_SECONDS
  };
}
