import React, { useState, useEffect } from 'react';
import { Minus, Square, Copy, X, Headphones } from 'lucide-react';

// Custom title bar for the frameless Electron window. Renders nothing
// outside Electron (e.g. when previewing the app in a regular browser tab),
// since there is no native chrome to replace there.
const TitleBar: React.FC = () => {
  const [isMaximized, setIsMaximized] = useState(true);
  const hasElectron = !!window.electron;

  useEffect(() => {
    if (!hasElectron) return;

    window.electron!.isWindowMaximized().then(setIsMaximized);
    window.electron!.onWindowMaximizedChange(setIsMaximized);
  }, [hasElectron]);

  if (!hasElectron) {
    return null;
  }

  return (
    <div className="title-bar">
      <div className="title-bar-side" />
      <div className="title-bar-center">
        <span className="title-bar-logo">
          <Headphones size={11} />
        </span>
        <span className="title-bar-title">Audook</span>
      </div>
      <div className="title-bar-side title-bar-controls">
        <button onClick={() => window.electron!.minimizeWindow()} title="Réduire">
          <Minus size={15} />
        </button>
        <button onClick={() => window.electron!.toggleMaximizeWindow()} title={isMaximized ? 'Restaurer' : 'Agrandir'}>
          {isMaximized ? <Copy size={13} /> : <Square size={13} />}
        </button>
        <button className="title-bar-close" onClick={() => window.electron!.closeWindow()} title="Fermer">
          <X size={16} />
        </button>
      </div>
    </div>
  );
};

export default TitleBar;
