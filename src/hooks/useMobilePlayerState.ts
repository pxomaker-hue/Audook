import { useEffect, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '../config';
import { mobilePlayerStore, MobilePlayerState, EqualizerPreset } from '../native/mobilePlayerStore';

// Mobile (Capacitor/Android) counterpart to usePlayerState.ts. Mirrors its
// PlayerState shape closely enough for Player.tsx to swap between the two,
// but drives the native AudookPlayer plugin (ExoPlayer + MediaSession)
// instead of the desktop backend's VLC/Chromecast player - mobile plays
// audio outside the PlayerService session entirely (see mobilePlayerStore).
const SEEK_STEP_SECONDS = 30;
// Same cycle as usePlayerState.ts's SPEEDS, kept in sync manually since
// mobile has no equivalent import to share it from (the desktop hook talks
// to the backend's own player session, this one to the native plugin).
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];

export function usePlayerState() {
  const [native, setNative] = useState<MobilePlayerState>(mobilePlayerStore.getState());
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [bookmarkAdded, setBookmarkAdded] = useState(false);
  const [equalizerPresets, setEqualizerPresets] = useState<EqualizerPreset[]>([]);

  useEffect(() => {
    return mobilePlayerStore.subscribe(setNative);
  }, []);

  useEffect(() => {
    mobilePlayerStore.fetchEqualizerPresets().then(setEqualizerPresets);
  }, []);

  const state = {
    isPlaying: native.isPlaying,
    currentBook: native.currentBook,
    currentChapterTitle: native.currentBook?.chapters?.[native.currentChapterIndex]?.title ?? null,
    currentChapterIndex: native.currentChapterIndex,
    position: native.position,
    duration: native.duration,
    volume: 100,
    speed: native.speed,
    equalizerPresetId: native.equalizerPresetId,
    loudnessNormalizationEnabled: native.loudnessNormalizationEnabled,
    compressionPreset: null,
    sleepTimerRemainingSeconds: null,
    isCasting: false,
    castDeviceName: null
  };

  const handlePlayPause = () => mobilePlayerStore.togglePlayPause();
  const handlePreviousClick = () => mobilePlayerStore.goToPreviousChapter();
  const handleNextClick = () => mobilePlayerStore.goToNextChapter();

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    mobilePlayerStore.seek(percentage * state.duration);
  };

  const handleSeekStep = (deltaSeconds: number) => mobilePlayerStore.seekStep(deltaSeconds);

  // Volume/equalizer/cast are desktop (VLC/Chromecast) features with no
  // equivalent wired into the native ExoPlayer plugin yet - no-ops here
  // rather than pretending to support them.
  const handleVolumeChange = (_volume: number) => {};
  const handleCycleSpeed = () => {
    const currentIndex = SPEEDS.indexOf(state.speed);
    const nextSpeed = SPEEDS[(currentIndex + 1) % SPEEDS.length] ?? 1;
    mobilePlayerStore.setSpeed(nextSpeed);
  };
  const handleCycleEqualizer = async () => {
    await mobilePlayerStore.cycleEqualizer();
  };
  const handleToggleLoudnessNormalization = () => {
    mobilePlayerStore.toggleLoudnessNormalization(!state.loudnessNormalizationEnabled);
  };
  const handleCycleCompression = async () => {};
  const handleCycleSleepTimer = async () => {};
  const handleScanCastDevices = async () => {};
  const handleConnectCastDevice = async (_deviceName: string) => {};
  const handleDisconnectCastDevice = async () => {};

  const handleAddBookmark = async () => {
    if (!state.currentBook) return;
    try {
      setAddingBookmark(true);
      await axios.post(`${getApiBase()}/books/${state.currentBook.id}/bookmarks`, {
        chapter_index: state.currentChapterIndex,
        position_seconds: state.position
      });
      setBookmarkAdded(true);
      setTimeout(() => setBookmarkAdded(false), 1800);
    } catch (error) {
      console.error('Failed to add bookmark:', error);
    } finally {
      setAddingBookmark(false);
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
    castDevices: [] as any[],
    castScanning: false,
    castConnecting: null as string | null,
    handleScanCastDevices,
    handleConnectCastDevice,
    handleDisconnectCastDevice,
    SEEK_STEP_SECONDS
  };
}
