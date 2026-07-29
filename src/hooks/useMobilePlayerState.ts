import { useEffect, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '../config';
import { mobilePlayerStore, MobilePlayerState } from '../native/mobilePlayerStore';

// Mobile (Capacitor/Android) counterpart to usePlayerState.ts. Mirrors its
// PlayerState shape closely enough for Player.tsx to swap between the two,
// but drives the native AudookPlayer plugin (ExoPlayer + MediaSession)
// instead of the desktop backend's VLC/Chromecast player - mobile plays
// audio outside the PlayerService session entirely (see mobilePlayerStore).
const SEEK_STEP_SECONDS = 30;

export function usePlayerState() {
  const [native, setNative] = useState<MobilePlayerState>(mobilePlayerStore.getState());
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [bookmarkAdded, setBookmarkAdded] = useState(false);

  useEffect(() => {
    return mobilePlayerStore.subscribe(setNative);
  }, []);

  const state = {
    isPlaying: native.isPlaying,
    currentBook: native.currentBook,
    currentChapterTitle: native.currentBook?.chapters?.[native.currentChapterIndex]?.title ?? null,
    currentChapterIndex: native.currentChapterIndex,
    position: native.position,
    duration: native.duration,
    volume: 100,
    speed: 1,
    equalizerPresetId: null,
    loudnessNormalizationEnabled: false,
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

  // Volume/speed/equalizer/cast are desktop (VLC/Chromecast) features with
  // no equivalent wired into the native ExoPlayer plugin yet - no-ops here
  // rather than pretending to support them.
  const handleVolumeChange = (_volume: number) => {};
  const handleCycleSpeed = () => {};
  const handleCycleEqualizer = async () => {};
  const handleToggleLoudnessNormalization = () => {};
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
    equalizerPresets: [] as any[],
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
