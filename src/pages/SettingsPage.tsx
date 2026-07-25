import React, { useState } from 'react';

const SettingsPage: React.FC = () => {
  const [theme, setTheme] = useState('dark');
  const [volume, setVolume] = useState(80);
  const [autoSync, setAutoSync] = useState(true);

  const handleSave = () => {
    localStorage.setItem('theme', theme);
    localStorage.setItem('volume', volume.toString());
    localStorage.setItem('autoSync', autoSync.toString());
    alert('Paramètres sauvegardés');
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Paramètres</h1>
        <p className="page-subtitle">Personnalisez votre expérience</p>
      </div>

      <div
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '30px',
          maxWidth: '600px'
        }}
      >
        <div style={{ marginBottom: '25px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-primary)' }}>
            Thème
          </label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: 'var(--background)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: '6px'
            }}
          >
            <option value="dark">Sombre</option>
            <option value="light">Clair</option>
            <option value="auto">Auto</option>
          </select>
        </div>

        <div style={{ marginBottom: '25px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-primary)' }}>
            Volume par défaut
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={volume}
            onChange={(e) => setVolume(parseInt(e.target.value))}
            style={{ width: '100%', cursor: 'pointer' }}
          />
          <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '8px' }}>
            {volume}%
          </p>
        </div>

        <div style={{ marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="checkbox"
            id="autoSync"
            checked={autoSync}
            onChange={(e) => setAutoSync(e.target.checked)}
            style={{ cursor: 'pointer', width: '18px', height: '18px' }}
          />
          <label
            htmlFor="autoSync"
            style={{ color: 'var(--text-primary)', cursor: 'pointer', flex: 1 }}
          >
            Synchronisation automatique
          </label>
        </div>

        <button
          onClick={handleSave}
          style={{
            background: 'var(--primary)',
            color: 'var(--secondary)',
            border: 'none',
            padding: '12px 30px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 600
          }}
        >
          Enregistrer les paramètres
        </button>
      </div>

      <div
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '30px',
          maxWidth: '600px',
          marginTop: '30px'
        }}
      >
        <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>À propos</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
          <strong>Audook</strong> v1.0.0
        </p>
        <p style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
          Lecteur d'audiolivres moderne et élégant pour Windows
        </p>
      </div>
    </div>
  );
};

export default SettingsPage;
