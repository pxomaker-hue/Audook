import React, { useState, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Settings } from 'lucide-react';
import axios from 'axios';

interface PlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  position: number;
  duration: number;
  volume: number;
  speed: number;
}

const Player: React.FC = () => {
  const [state, setState] = useState<PlayerState>({
    isPlaying: false,
    currentBook: null,
    position: 0,
    duration: 0,
    volume: 80,
    speed: 1
  });

  const apiBase = 'http://localhost:5000/api';

  useEffect(() => {
    // Get initial player state
    const fetchState = async () => {
      try {
        const response = await axios.get(`${apiBase}/player/state`);
        setState(prev => ({ ...prev, ...response.data }));
      } catch (error) {
        console.error('Failed to get player state:', error);
      }
    };

    fetchState();

    // Listen for player events if using IPC
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
        await axios.post(`${apiBase}/player/pause`);
      } else {
        await axios.post(`${apiBase}/player/resume`);
      }
      setState(prev => ({ ...prev, isPlaying: !prev.isPlaying }));
    } catch (error) {
      console.error('Failed to toggle playback:', error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const bar = e.currentTarget;
    const rect = bar.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    const newPosition = percentage * state.duration;

    setState(prev => ({ ...prev, position: newPosition }));
    axios.post(`${apiBase}/player/seek`, { position: newPosition });
  };

  const handleVolumeChange = (volume: number) => {
    setState(prev => ({ ...prev, volume }));
    axios.post(`${apiBase}/player/volume`, { volume });
  };

  const handleSpeedChange = (speed: number) => {
    setState(prev => ({ ...prev, speed }));
    axios.post(`${apiBase}/player/speed`, { speed });
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
        <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Sélectionnez un livre pour commencer
        </div>
      </div>
    );
  }

  const percentage = state.duration ? (state.position / state.duration) * 100 : 0;

  return (
    <div className="player">
      <div className="player-info">
        <div className="player-cover">
          {state.currentBook.cover_url && (
            <img src={state.currentBook.cover_url} alt={state.currentBook.title} />
          )}
        </div>
        <div className="player-details">
          <div className="player-title">{state.currentBook.title}</div>
          <div className="player-author">{state.currentBook.author}</div>
        </div>
        <div className="player-controls">
          <button className="player-button" onClick={handlePlayPause} title={state.isPlaying ? 'Pause' : 'Lecture'}>
            {state.isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </button>
          <select
            value={state.speed}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
            style={{
              background: 'var(--surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '5px 10px',
              cursor: 'pointer'
            }}
          >
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
            style={{
              width: '80px',
              cursor: 'pointer'
            }}
            title="Volume"
          />
        </div>
      </div>

      <div className="player-progress">
        <span className="player-time">{formatTime(state.position)}</span>
        <div className="progress-bar" onClick={handleSeek}>
          <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
        </div>
        <span className="player-time">{formatTime(state.duration)}</span>
      </div>
    </div>
  );
};

export default Player;
