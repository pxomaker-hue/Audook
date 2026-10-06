import React from 'react';
import { useDialogA11y } from '../hooks/useDialogA11y';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  message,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  danger = false,
  onConfirm,
  onCancel
}) => {
  const dialogRef = useDialogA11y<HTMLDivElement>(open, onCancel);

  if (!open) return null;

  return (
    <div className="confirm-dialog-backdrop" onClick={onCancel}>
      <div
        className="confirm-dialog"
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-dialog-title" className="confirm-dialog-title">{title}</h3>
        <p id="confirm-dialog-message" className="confirm-dialog-message">{message}</p>
        <div className="confirm-dialog-actions">
          <button className="confirm-dialog-cancel" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            className={`confirm-dialog-confirm ${danger ? 'danger' : ''}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
