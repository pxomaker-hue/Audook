import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, ListMusic, Volume1, Volume2, VolumeX } from 'lucide-react';
import axios from 'axios';

// Click window (ms) to detect a double-click on the "previous chapter" button
const PREVIOUS_DOUBLE_CLICK_WINDOW = 300;
// Below this many elapsed seconds, a single click on "previous" also jumps to
// the previous chapter instead of just restarting the current one.
const RESTART_THRESHOLD_SECONDS = 2;
const SEEK_STEP_SECONDS = 30;
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

interface PlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  currentChapterTitle: string | null;
  position: number;
  duration: number;
  volume: number;
  speed: number;
}

// Stable pseudo-random bar heights for the waveform decoration
const WAVE_BARS = Array.from({ length: 32 }, (_, i) => {
  const seed = Math.sin(i * 12.9898) * 43758.5453;
  return 8 + Math.round((seed - Math.floor(seed)) * 24);
});

const VolumeIcon = ({ volume }: { volume: number }) => {
  if (volume === 0) return <VolumeX size={16} />;
  if (volume < 50) return <Volume1 size={16} />;
  return <Volume2 size={16} />;
};

const Player: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<PlayerState>({
    isPlaying: false,
    currentBook: null,
    currentChapterTitle: null,
    position: 0,
    duration: 0,
    volume: 80,
    speed: 1
  });
  const [showVolume, setShowVolume] = useState(false);
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

  useEffect(() => {
    return () => {
      if (previousClickTimer.current) {
        clearTimeout(previousClickTimer.current);
      }
    };
  }, []);

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

  const handleCycleSpeed = () => {
    const currentIndex = SPEEDS.indexOf(state.speed);
    const nextSpeed = SPEEDS[(currentIndex + 1) % SPEEDS.length] ?? 1;
    setState(prev => ({ ...prev, speed: nextSpeed }));
    axios.post(`${API_BASE}/player/speed`, { speed: nextSpeed });
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!state.currentBook) {
    return (
      <div className="player">
        <div className="player-empty">Sélectionnez un livre pour commencer</div>
      </div>
    );
  }

  const percentage = state.duration ? (state.position / state.duration) * 100 : 0;

  return (
    <div className="player">
      <div className="player-title-bar">{state.currentBook.title}</div>

      <div className="player-cover-wrap">
        {state.currentBook.cover_url && (
          <div
            className="player-cover-glow"
            style={{ backgroundImage: `url(${state.currentBook.cover_url})` }}
          />
        )}
        <div className="player-cover">
          {state.currentBook.cover_url ? (
            <img src={state.currentBook.cover_url} alt={state.currentBook.title} />
          ) : (
            <span>📚</span>
          )}
        </div>
      </div>

      {state.currentChapterTitle && (
        <div className="player-current-chapter">{state.currentChapterTitle}</div>
      )}
      <div className="player-author">{state.currentBook.author}</div>

      {state.currentBook.description && (
        <div className="player-description">{state.currentBook.description}</div>
      )}

      <div className={`player-waveform ${state.isPlaying ? 'playing' : ''}`}>
        {WAVE_BARS.map((h, i) => (
          <span key={i} style={{ height: `${h}px` }} />
        ))}
      </div>

      <div className="player-progress">
        <div className="progress-bar" onClick={handleSeek}>
          <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
        </div>
        <div className="player-time-row">
          <span className="player-time">{formatTime(state.position)}</span>
          <span className="player-time">{formatTime(state.duration)}</span>
        </div>
      </div>

      <div className="player-controls">
        <button
          className="player-button"
          onClick={handlePreviousClick}
          title="Chapitre précédent (2 clics) / Redémarrer le chapitre (1 clic)"
        >
          <SkipBack size={16} />
        </button>
        <button className="player-button" onClick={() => handleSeekStep(-SEEK_STEP_SECONDS)} title="Reculer de 30s">
          <Rewind size={16} />
        </button>
        <button
          className="player-button main"
          onClick={handlePlayPause}
          title={state.isPlaying ? 'Pause' : 'Lecture'}
        >
          {state.isPlaying ? <Pause size={22} /> : <Play size={22} />}
        </button>
        <button className="player-button" onClick={() => handleSeekStep(SEEK_STEP_SECONDS)} title="Avancer de 30s">
          <FastForward size={16} />
        </button>
        <button className="player-button" onClick={handleNextClick} title="Chapitre suivant">
          <SkipForward size={16} />
        </button>
      </div>

      <div className="player-extra-row">
        <button
          className="player-button"
          onClick={() => navigate(`/book/${state.currentBook.id}`)}
          title="Voir les chapitres"
        >
          <ListMusic size={16} />
        </button>
        <button className="speed-pill" onClick={handleCycleSpeed} title="Vitesse de lecture">
          {state.speed}×
        </button>
        <div className="volume-popover-wrapper" ref={volumeWrapperRef}>
          {showVolume && (
            <div className="volume-popover">
              <input
                type="range"
                className="volume-slider-vertical"
                min="0"
                max="100"
                value={state.volume}
                onChange={(e) => handleVolumeChange(parseInt(e.target.value))}
              />
            </div>
          )}
          <button
            className="player-button"
            onClick={() => setShowVolume(!showVolume)}
            title="Volume"
          >
            <VolumeIcon volume={state.volume} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Player;
