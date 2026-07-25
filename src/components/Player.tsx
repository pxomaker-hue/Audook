import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, Rewind, FastForward, ListMusic, Volume2 } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

interface PlayerState {
  isPlaying: boolean;
  currentBook: any | null;
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

const Player: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<PlayerState>({
    isPlaying: false,
    currentBook: null,
    position: 0,
    duration: 0,
    volume: 80,
    speed: 1
  });
  const [showExtra, setShowExtra] = useState(false);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const response = await axios.get(`${API_BASE}/player/state`);
        setState(prev => ({ ...prev, ...response.data }));
      } catch (error) {
        console.error('Failed to get player state:', error);
      }
    };

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

  const handlePlayPause = async () => {
    try {
      if (state.isPlaying) {
        await axios.post(`${API_BASE}/player/pause`);
      } else {
        await axios.post(`${API_BASE}/player/resume`);
      }
      setState(prev => ({ ...prev, isPlaying: !prev.isPlaying }));
    } catch (error) {
      console.error('Failed to toggle playback:', error);
    }
  };

  const handleSkip = async (deltaSeconds: number) => {
    const newPosition = Math.max(0, Math.min(state.duration, state.position + deltaSeconds));
    setState(prev => ({ ...prev, position: newPosition }));
    try {
      await axios.post(`${API_BASE}/player/seek`, { position: newPosition });
    } catch (error) {
      console.error('Failed to seek:', error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    const newPosition = percentage * state.duration;
    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${API_BASE}/player/seek`, { position: newPosition });
  };

  const handleVolumeChange = (volume: number) => {
    setState(prev => ({ ...prev, volume }));
    axios.post(`${API_BASE}/player/volume`, { volume });
  };

  const handleSpeedChange = (speed: number) => {
    setState(prev => ({ ...prev, speed }));
    axios.post(`${API_BASE}/player/speed`, { speed });
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
          onClick={() => navigate(`/book/${state.currentBook.id}`)}
          title="Voir les chapitres"
        >
          <ListMusic size={16} />
        </button>
        <button className="player-button" onClick={() => handleSkip(-30)} title="Reculer de 30s">
          <Rewind size={18} />
        </button>
        <button
          className="player-button main"
          onClick={handlePlayPause}
          title={state.isPlaying ? 'Pause' : 'Lecture'}
        >
          {state.isPlaying ? <Pause size={22} /> : <Play size={22} />}
        </button>
        <button className="player-button" onClick={() => handleSkip(30)} title="Avancer de 30s">
          <FastForward size={18} />
        </button>
        <button
          className="player-button"
          onClick={() => setShowExtra(!showExtra)}
          title="Volume et vitesse"
        >
          <Volume2 size={16} />
        </button>
      </div>

      {showExtra && (
        <div className="player-extra-row">
          <select value={state.speed} onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}>
            <option value={0.75}>0.75x</option>
            <option value={1}>1x</option>
            <option value={1.25}>1.25x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
          <input
            type="range"
            min="0"
            max="100"
            value={state.volume}
            onChange={(e) => handleVolumeChange(parseInt(e.target.value))}
            title="Volume"
          />
        </div>
      )}
    </div>
  );
};

export default Player;
