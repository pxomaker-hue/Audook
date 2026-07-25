import React from 'react';

const HistoryPage: React.FC = () => {
  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Historique</h1>
        <p className="page-subtitle">Vos audiolivres écoutés récemment</p>
      </div>

      <div
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '40px',
          textAlign: 'center',
          color: 'var(--text-secondary)'
        }}
      >
        <p style={{ fontSize: '16px', marginBottom: '10px' }}>Aucun audiolive dans l'historique</p>
        <p style={{ fontSize: '14px' }}>Vos audiolivres écoutés s'afficheront ici</p>
      </div>
    </div>
  );
};

export default HistoryPage;
