import { useEffect, useRef, useState } from 'react';
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
// MediaRouter discovery has no "scan finished" signal like desktop's
// blocking pychromecast scan does - devices stream in via castDevices as
// they're found during this window, then the "scanning" spinner just stops.
const CAST_SCAN_DURATION_MS = 6000;
// Discovery itself (the actual MediaRouter callback that keeps routes
// live/selectable) used to stop at the same 6s mark as the spinner - if the
// user took a moment to read the list before tapping a device, the route
// could already be gone from MediaRouter by the time connect() looked it up,
// which failed silently (no error surfaced) and looked like "nothing
// happens". Discovery now outlives the spinner by a lot more margin, and is
// cut short immediately on a successful connect instead of waiting on this.
const CAST_DISCOVERY_SAFETY_TIMEOUT_MS = 120000;

export function usePlayerState() {
  const [native, setNative] = useState<MobilePlayerState>(mobilePlayerStore.getState());
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [bookmarkAdded, setBookmarkAdded] = useState(false);
  const [equalizerPresets, setEqualizerPresets] = useState<EqualizerPreset[]>([]);
  const [castScanning, setCastScanning] = useState(false);
  const [castConnecting, setCastConnecting] = useState<string | null>(null);
  const [castError, setCastError] = useState<string | null>(null);
  const discoverySafetyTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    compressionPreset: native.compressionPreset,
    sleepTimerRemainingSeconds: null,
    isCasting: native.isCasting,
    castDeviceName: native.castDeviceName
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
  const handleCycleCompression = async () => {
    await mobilePlayerStore.cycleCompression();
  };
  const handleCycleSleepTimer = async () => {};
  const handleScanCastDevices = async () => {
    setCastError(null);
    setCastScanning(true);
    await mobilePlayerStore.scanCastDevices();
    // Only the spinner stops here - see CAST_DISCOVERY_SAFETY_TIMEOUT_MS for
    // why discovery itself needs to keep running well past this.
    setTimeout(() => setCastScanning(false), CAST_SCAN_DURATION_MS);
    if (discoverySafetyTimeout.current) clearTimeout(discoverySafetyTimeout.current);
    discoverySafetyTimeout.current = setTimeout(() => {
      mobilePlayerStore.stopCastDiscovery();
    }, CAST_DISCOVERY_SAFETY_TIMEOUT_MS);
  };
  const handleConnectCastDevice = async (deviceId: string) => {
    try {
      setCastError(null);
      setCastConnecting(deviceId);
      await mobilePlayerStore.connectCastDevice(deviceId);
      // Connected - no need to keep discovery running (and the device list
      // popover is about to close anyway).
      if (discoverySafetyTimeout.current) {
        clearTimeout(discoverySafetyTimeout.current);
        discoverySafetyTimeout.current = null;
      }
      await mobilePlayerStore.stopCastDiscovery();
    } catch (error) {
      console.error('Failed to connect to cast device:', error);
      setCastError("Impossible de se connecter à cet appareil. Réessayez, ou vérifiez qu'il est bien sur le même réseau.");
    } finally {
      setCastConnecting(null);
    }
  };
  const handleDisconnectCastDevice = async () => {
    await mobilePlayerStore.disconnectCastDevice();
  };

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
    castDevices: native.castDevices,
    castScanning,
    castConnecting,
    castError,
    handleScanCastDevices,
    handleConnectCastDevice,
    handleDisconnectCastDevice,
    SEEK_STEP_SECONDS
  };
}
