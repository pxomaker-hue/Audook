import React from 'react';
import { formatTime } from '../hooks/usePlayerState';

interface SeekBarProps {
  position: number;
  duration: number;
  onSeek: (e: React.MouseEvent<HTMLDivElement>) => void;
  onStep: (deltaSeconds: number) => void;
  label?: string;
}

const KEY_STEP_SECONDS = 10;
const PAGE_STEP_SECONDS = 60;

// Keyboard- and screen-reader-accessible progress bar: same visuals as the
// old <div className="progress-bar">, but exposed as an ARIA slider. Mouse
// seeking still goes through the player hook's onSeek (it reads clientX off
// the click event); arrow/page keys reuse the hook's relative onStep.
const SeekBar: React.FC<SeekBarProps> = ({ position, duration, onSeek, onStep, label = 'Position de lecture' }) => {
  const percentage = duration ? (position / duration) * 100 : 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const deltas: Record<string, number> = {
      ArrowRight: KEY_STEP_SECONDS,
      ArrowUp: KEY_STEP_SECONDS,
      ArrowLeft: -KEY_STEP_SECONDS,
      ArrowDown: -KEY_STEP_SECONDS,
      PageUp: PAGE_STEP_SECONDS,
      PageDown: -PAGE_STEP_SECONDS,
      Home: -duration,
      End: duration
    };
    const delta = deltas[e.key];
    if (delta === undefined) return;
    e.preventDefault();
    onStep(delta);
  };

  return (
    <div
      className="progress-bar"
      role="slider"
      tabIndex={0}
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
      aria-valuenow={Math.round(position)}
      aria-valuetext={`${formatTime(position)} sur ${formatTime(duration)}`}
      onClick={onSeek}
      onKeyDown={handleKeyDown}
    >
      <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
    </div>
  );
};

export default SeekBar;
