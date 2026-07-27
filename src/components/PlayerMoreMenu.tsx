import React, { useState, useRef, useEffect } from 'react';
import { MoreHorizontal, Gauge, Waves, SlidersHorizontal, Volume1, Volume2, VolumeX, Moon } from 'lucide-react';
import { EqualizerPreset } from '../hooks/usePlayerState';

interface PlayerMoreMenuProps {
  speed: number;
  onCycleSpeed: () => void;
  equalizerPresetId: string | null;
  equalizerPresets: EqualizerPreset[];
  onCycleEqualizer: () => void;
  normalizationEnabled: boolean;
  onToggleNormalization: () => void;
  volume: number;
  onVolumeChange: (volume: number) => void;
  sleepTimerRemainingSeconds: number | null;
  onCycleSleepTimer: () => void;
  buttonSize?: number;
}

const VolumeIcon = ({ volume }: { volume: number }) => {
  if (volume === 0) return <VolumeX size={16} />;
  if (volume < 50) return <Volume1 size={16} />;
  return <Volume2 size={16} />;
};

// Replaces the old standalone speed-pill button: a single "..." button that
// unfolds a small popover (upward, so it clears the player controls near the
// bottom of the window) with the three audio-tweak actions - speed,
// normalization, equalizer. Used by both the docked Player and the detached
// MiniPlayerView, which each hold their own usePlayerState() instance, so
// all the state/handlers come in as props rather than being read directly.
const PlayerMoreMenu: React.FC<PlayerMoreMenuProps> = ({
  speed,
  onCycleSpeed,
  equalizerPresetId,
  equalizerPresets,
  onCycleEqualizer,
  normalizationEnabled,
  onToggleNormalization,
  volume,
  onVolumeChange,
  sleepTimerRemainingSeconds,
  onCycleSleepTimer,
  buttonSize = 16
}) => {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const equalizerName = equalizerPresetId
    ? equalizerPresets.find(p => p.id === equalizerPresetId)?.name || '...'
    : 'Off';

  const sleepTimerLabel = (() => {
    if (sleepTimerRemainingSeconds === null) return 'Off';
    const totalSeconds = Math.round(sleepTimerRemainingSeconds);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  })();

  return (
    <div className="more-menu-wrapper" ref={wrapperRef}>
      {open && (
        <div className="more-menu-popover">
          <div className="more-menu-row">
            <span className="more-menu-label">
              Vitesse <b>{speed}×</b>
            </span>
            <button className="player-button more-menu-icon" onClick={onCycleSpeed} title="Changer la vitesse de lecture">
              <Gauge size={16} />
            </button>
          </div>
          <div className="more-menu-row">
            <span className="more-menu-label">
              Normalisation <b>{normalizationEnabled ? 'Activée' : 'Off'}</b>
            </span>
            <button
              className={`player-button more-menu-icon ${normalizationEnabled ? 'confirmed' : ''}`}
              onClick={onToggleNormalization}
              title="Lisser les écarts de volume"
            >
              <Waves size={16} />
            </button>
          </div>
          <div className="more-menu-row">
            <span className="more-menu-label">
              Égaliseur <b>{equalizerName}</b>
            </span>
            <button className="player-button more-menu-icon" onClick={onCycleEqualizer} title="Changer de préréglage d'égaliseur">
              <SlidersHorizontal size={16} />
            </button>
          </div>
          <div className="more-menu-row">
            <div className="more-menu-volume-slider">
              <input
                type="range"
                min="0"
                max="100"
                value={volume}
                onChange={(e) => onVolumeChange(parseInt(e.target.value))}
              />
            </div>
            <button className="player-button more-menu-icon" title="Volume">
              <VolumeIcon volume={volume} />
            </button>
          </div>
          <div className="more-menu-row">
            <span className="more-menu-label">
              Minuteur de veille <b>{sleepTimerLabel}</b>
            </span>
            <button
              className={`player-button more-menu-icon ${sleepTimerRemainingSeconds !== null ? 'confirmed' : ''}`}
              onClick={onCycleSleepTimer}
              title="Minuteur de veille"
            >
              <Moon size={16} />
            </button>
          </div>
        </div>
      )}
      <button className="player-button" onClick={() => setOpen(!open)} title="Plus d'options audio">
        <MoreHorizontal size={buttonSize} />
      </button>
    </div>
  );
};

export default PlayerMoreMenu;
