import React from 'react';

interface ExpandActionProps {
  icon: React.ReactNode;
  label: string;
  title?: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'confirmed';
}

// Round icon button whose label slides out on hover or keyboard focus (the
// CSS lives in App.css as .icon-expand-*). The inner <button> is the real
// focus/activation target; the wrapper only forwards clicks on the label.
const ExpandAction: React.FC<ExpandActionProps> = ({ icon, label, title, onClick, disabled, variant }) => (
  <div
    className="icon-expand-wrapper"
    role="presentation"
    onClick={() => !disabled && onClick()}
  >
    <button
      type="button"
      className={`icon-expand-button ${variant ?? ''}`}
      disabled={disabled}
      title={title ?? label}
      aria-label={label}
    >
      {icon}
    </button>
    <span className="icon-expand-label" aria-hidden="true">{label}</span>
  </div>
);

export default ExpandAction;
