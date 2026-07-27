import React, { useState, useRef, useEffect } from 'react';
import { Volume1, Volume2, VolumeX } from 'lucide-react';

interface VolumeControlProps {
  volume: number;
  onChange: (volume: number) => void;
  size?: number;
}

const VolumeIcon = ({ volume }: { volume: number }) => {
  if (volume === 0) return <VolumeX size={16} />;
  if (volume < 50) return <Volume1 size={16} />;
  return <Volume2 size={16} />;
};

// Self-contained: owns its own open state + click-outside ref, so it works
// correctly even when several instances exist in the DOM at once (the full
// and compact player layouts are both always mounted, CSS just picks which
// one is visible) - sharing a single ref/state across instances meant the
// outside-click listener could end up watching the wrong (hidden) instance,
// closing the popover the moment you clicked inside the visible one.
const VolumeControl: React.FC<VolumeControlProps> = ({ volume, onChange, size = 16 }) => {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  return (
    <div className="volume-popover-wrapper" ref={wrapperRef}>
      {open && (
        <div className="volume-popover">
          <input
            type="range"
            className="volume-slider-vertical"
            min="0"
            max="100"
            value={volume}
            onChange={(e) => onChange(parseInt(e.target.value))}
          />
        </div>
      )}
      <button className="player-button" onClick={() => setOpen(!open)} title="Volume">
        <VolumeIcon volume={volume} />
      </button>
    </div>
  );
};

export default VolumeControl;
