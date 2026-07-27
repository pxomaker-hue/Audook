import React, { useState, useRef, useEffect } from 'react';
import { MoreHorizontal, Gauge, SlidersHorizontal, Volume1, Volume2, VolumeX, Moon, AudioLines, Activity, Cast, RefreshCw, Loader2, X } from 'lucide-react';
import { EqualizerPreset, CastDevice } from '../hooks/usePlayerState';

interface PlayerMoreMenuProps {
  speed: number;
  onCycleSpeed: () => void;
  equalizerPresetId: string | null;
  equalizerPresets: EqualizerPreset[];
  onCycleEqualizer: () => void;
  loudnessNormalizationEnabled: boolean;
  onToggleLoudnessNormalization: () => void;
  compressionPreset: string | null;
  onCycleCompression: () => void;
  volume: number;
  onVolumeChange: (volume: number) => void;
  // The classic/compact Player already has a standalone volume button next
  // to this menu, so its volume row here would be a redundant duplicate -
  // the mini-player has no such standalone button, so it needs this row.
  // Defaults to shown (mini-player's case) so existing callers don't need
  // updating.
  showVolume?: boolean;
  sleepTimerRemainingSeconds: number | null;
  onCycleSleepTimer: () => void;
  isCasting: boolean;
  castDeviceName: string | null;
  castDevices: CastDevice[];
  castScanning: boolean;
  castConnecting: string | null;
  onScanCast: () => void;
  onConnectCast: (deviceName: string) => void;
  onDisconnectCast: () => void;
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
  loudnessNormalizationEnabled,
  onToggleLoudnessNormalization,
  compressionPreset,
  onCycleCompression,
  volume,
  onVolumeChange,
  showVolume = true,
  sleepTimerRemainingSeconds,
  onCycleSleepTimer,
  isCasting,
  castDeviceName,
  castDevices,
  castScanning,
  castConnecting,
  onScanCast,
  onConnectCast,
  onDisconnectCast,
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

  const compressionLabel = compressionPreset === 'leger' ? 'Léger'
    : compressionPreset === 'modere' ? 'Modéré'
    : compressionPreset === 'fort' ? 'Fort'
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
              Volume EBU <b>{loudnessNormalizationEnabled ? 'Activée' : 'Off'}</b>
            </span>
            <button
              className={`player-button more-menu-icon ${loudnessNormalizationEnabled ? 'confirmed' : ''}`}
              onClick={onToggleLoudnessNormalization}
              title="Égaliser le volume moyen entre les livres"
            >
              <AudioLines size={16} />
            </button>
          </div>
          <div className="more-menu-row">
            <span className="more-menu-label">
              Compression <b>{compressionLabel}</b>
            </span>
            <button
              className={`player-button more-menu-icon ${compressionPreset ? 'confirmed' : ''}`}
              onClick={onCycleCompression}
              title="Compression dynamique (resserre les écarts de volume)"
            >
              <Activity size={16} />
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
          {showVolume && (
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
          )}
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
          {isCasting ? (
            <div className="more-menu-row">
              <span className="more-menu-label">
                Diffusion sur <b>{castDeviceName}</b>
              </span>
              <button
                className="player-button more-menu-icon"
                onClick={onDisconnectCast}
                title="Arrêter la diffusion (revenir à la lecture locale)"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <>
              <div className="more-menu-row">
                <span className="more-menu-label">Google Home / Chromecast</span>
                <button
                  className="player-button more-menu-icon"
                  onClick={onScanCast}
                  disabled={castScanning}
                  title="Rechercher les appareils sur le réseau"
                >
                  {castScanning ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
                </button>
              </div>
              {castDevices.map(device => (
                <div className="more-menu-row" key={device.uuid}>
                  <span className="more-menu-label">{device.name}</span>
                  <button
                    className="player-button more-menu-icon"
                    onClick={() => onConnectCast(device.name)}
                    disabled={castConnecting === device.name}
                    title={`Diffuser sur ${device.name}`}
                  >
                    {castConnecting === device.name ? <Loader2 size={16} className="spin" /> : <Cast size={16} />}
                  </button>
                </div>
              ))}
            </>
          )}
        </div>
      )}
      <button className="player-button" onClick={() => setOpen(!open)} title="Plus d'options audio">
        <MoreHorizontal size={buttonSize} />
      </button>
    </div>
  );
};

export default PlayerMoreMenu;
