import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

// Click window (ms) to detect a double-click on the "previous chapter" button
const PREVIOUS_DOUBLE_CLICK_WINDOW = 300;
// Below this many elapsed seconds, a single click on "previous" also jumps to
// the previous chapter instead of just restarting the current one.
const RESTART_THRESHOLD_SECONDS = 2;
const SEEK_STEP_SECONDS = 30;
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

export interface PlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  currentChapterTitle: string | null;
  currentChapterIndex: number | null;
  position: number;
  duration: number;
  volume: number;
  speed: number;
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
    speed: 1
  });
  const [showVolume, setShowVolume] = useState(false);
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [bookmarkAdded, setBookmarkAdded] = useState(false);
  const previousClickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const volumeWrapperRef = useRef<HTMLDivElement>(null);

  const fetchState = async () => {
    try {
      const response = await axios.get(`${API_BASE}/player/state`);
      // Backend uses snake_case (is_playing); explicitly map it instead of
      // relying on the spread, otherwise `isPlaying` never actually updates.
      setState(prev => ({
        ...prev,
        ...response.data,
        isPlaying: response.data.is_playing ?? prev.isPlaying
      }));
    } catch (error) {
      console.error('Failed to get player state:', error);
    }
  };

  useEffect(() => {
    fetchState();

    if (window.electron?.onPlayerState) {
      window.electron.onPlayerState((newState: any) => {
        setState(prev => ({ ...prev, ...newState }));
      });
    }

    if (window.electron?.onPlayerPosition) {
      window.electron.onPlayerPosition((data: any) => {
        setState(prev => ({ ...prev, position: data.position }));
      });
    }

    const interval = setInterval(fetchState, 1000);
    return () => clearInterval(interval);
  }, []);

  // Close the volume popover when clicking outside of it
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (volumeWrapperRef.current && !volumeWrapperRef.current.contains(e.target as Node)) {
        setShowVolume(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    return () => {
      if (previousClickTimer.current) {
        clearTimeout(previousClickTimer.current);
      }
    };
  }, []);

  const handlePlayPause = async () => {
    try {
      if (state.isPlaying) {
        await axios.post(`${API_BASE}/player/pause`);
      } else {
        await axios.post(`${API_BASE}/player/resume`);
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
      await axios.post(`${API_BASE}/player/previous-chapter`);
    } catch (error) {
      console.error('Failed to go to previous chapter:', error);
    }
  };

  const restartChapter = async () => {
    setState(prev => ({ ...prev, position: 0 }));
    try {
      await axios.post(`${API_BASE}/player/seek`, { position: 0 });
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
      await axios.post(`${API_BASE}/player/next-chapter`);
    } catch (error) {
      console.error('Failed to go to next chapter:', error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    const newPosition = percentage * state.duration;
    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${API_BASE}/player/seek`, { position: newPosition });
  };

  const handleSeekStep = (deltaSeconds: number) => {
    const newPosition = Math.max(0, Math.min(state.duration, state.position + deltaSeconds));
    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${API_BASE}/player/seek`, { position: newPosition });
  };

  const handleVolumeChange = (volume: number) => {
    setState(prev => ({ ...prev, volume }));
    axios.post(`${API_BASE}/player/volume`, { volume });
  };

  const handleAddBookmark = async () => {
    if (!state.currentBook) return;
    try {
      setAddingBookmark(true);
      await axios.post(`${API_BASE}/books/${state.currentBook.id}/bookmarks`, {});
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
    axios.post(`${API_BASE}/player/speed`, { speed: nextSpeed });
  };

  return {
    state,
    showVolume,
    setShowVolume,
    addingBookmark,
    bookmarkAdded,
    volumeWrapperRef,
    handlePlayPause,
    handlePreviousClick,
    handleNextClick,
    handleSeek,
    handleSeekStep,
    handleVolumeChange,
    handleAddBookmark,
    handleCycleSpeed,
    SEEK_STEP_SECONDS
  };
}
