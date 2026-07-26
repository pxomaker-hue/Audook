import React, { useState } from 'react';
import { CloseBehavior } from '../electron';

interface CloseAppDialogProps {
  open: boolean;
  onChoice: (action: CloseBehavior, remember: boolean) => void;
}

// Shown when the close button (or Alt+F4) is pressed and no close behavior
// has been remembered yet - see the mainWindow 'close' handler in
// electron/main.js. Reuses the .confirm-dialog shell (see ConfirmDialog) but
// needs its own two-choice + checkbox layout, not a plain confirm/cancel.
const CloseAppDialog: React.FC<CloseAppDialogProps> = ({ open, onChoice }) => {
  const [remember, setRemember] = useState(false);

  if (!open) return null;

  return (
    <div className="confirm-dialog-backdrop">
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <h3 className="confirm-dialog-title">Fermer Audook ?</h3>
        <p className="confirm-dialog-message">
          Vous pouvez fermer complètement l'application, ou la réduire dans la barre système - la lecture continuera en arrière-plan.
        </p>
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '20px',
            fontSize: '13px',
            color: 'var(--text-secondary)',
            cursor: 'pointer'
          }}
        >
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            style={{ cursor: 'pointer', width: '16px', height: '16px' }}
          />
          Se souvenir de mon choix
        </label>
        <div className="confirm-dialog-actions">
          <button className="confirm-dialog-cancel" onClick={() => onChoice('tray', remember)}>
            Réduire dans la barre système
          </button>
          <button className="confirm-dialog-confirm danger" onClick={() => onChoice('quit', remember)}>
            Fermer l'application
          </button>
        </div>
      </div>
    </div>
  );
};

export default CloseAppDialog;
