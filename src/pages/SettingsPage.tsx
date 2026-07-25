import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

type ServerType = 'plex' | 'audiobookshelf' | 'local';

interface ServerEntry {
  id: string;
  type: ServerType;
  name: string;
  url: string;
  sync_enabled: boolean;
  last_sync: string | null;
}

const TYPE_LABELS: Record<ServerType, string> = {
  plex: 'Plex',
  audiobookshelf: 'Audiobookshelf',
  local: 'Dossier local'
};

const cardStyle: React.CSSProperties = {
  backgroundColor: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  padding: '30px',
  maxWidth: '600px',
  marginTop: '30px'
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px',
  backgroundColor: 'var(--background)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: '6px'
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  color: 'var(--text-primary)'
};

const buttonStyle: React.CSSProperties = {
  background: 'var(--primary)',
  color: 'var(--secondary)',
  border: 'none',
  padding: '10px 20px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 600
};

const secondaryButtonStyle: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  padding: '8px 14px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '13px'
};

const SettingsPage: React.FC = () => {
  const [theme, setTheme] = useState('dark');
  const [volume, setVolume] = useState(80);
  const [autoSync, setAutoSync] = useState(true);

  const [servers, setServers] = useState<ServerEntry[]>([]);
  const [loadingServers, setLoadingServers] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formType, setFormType] = useState<ServerType>('audiobookshelf');
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formApiKey, setFormApiKey] = useState('');
  const [formUsername, setFormUsername] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [busyServerId, setBusyServerId] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);

  const loadServers = useCallback(async () => {
    try {
      setLoadingServers(true);
      const response = await axios.get(`${API_BASE}/servers`);
      setServers(response.data);
    } catch (error) {
      console.error('Failed to load servers:', error);
    } finally {
      setLoadingServers(false);
    }
  }, []);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const handleSave = () => {
    localStorage.setItem('theme', theme);
    localStorage.setItem('volume', volume.toString());
    localStorage.setItem('autoSync', autoSync.toString());
    alert('Paramètres sauvegardés');
  };

  const resetForm = () => {
    setFormName('');
    setFormUrl('');
    setFormApiKey('');
    setFormUsername('');
    setFormPassword('');
    setFormError(null);
  };

  const handleBrowseFolder = async () => {
    if (!window.electron) {
      setFormError("Sélection de dossier indisponible hors de l'application Electron");
      return;
    }
    const folder = await window.electron.selectFolder();
    if (folder) {
      setFormUrl(folder);
      if (!formName) {
        const parts = folder.split(/[\\/]/).filter(Boolean);
        setFormName(parts[parts.length - 1] || 'Dossier local');
      }
    }
  };

  const handleAddServer = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formName.trim() || !formUrl.trim()) {
      setFormError('Le nom et l\'URL (ou le dossier) sont requis');
      return;
    }

    const payload: any = { type: formType, name: formName.trim(), url: formUrl.trim() };
    if (formType === 'plex') {
      payload.api_key = formApiKey.trim();
    } else if (formType === 'audiobookshelf') {
      payload.username = formUsername.trim();
      payload.password = formPassword;
    }

    try {
      setSubmitting(true);
      await axios.post(`${API_BASE}/servers`, payload);
      resetForm();
      setShowAddForm(false);
      await loadServers();
    } catch (error: any) {
      setFormError(error?.response?.data?.error || 'Impossible de se connecter au serveur');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteServer = async (id: string, name: string) => {
    if (!window.confirm(`Supprimer le serveur "${name}" ?`)) return;
    try {
      setBusyServerId(id);
      await axios.delete(`${API_BASE}/servers/${id}`);
      await loadServers();
    } catch (error) {
      console.error('Failed to delete server:', error);
    } finally {
      setBusyServerId(null);
    }
  };

  const handleScanServer = async (id: string) => {
    try {
      setBusyServerId(id);
      await axios.post(`${API_BASE}/servers/${id}/scan`);
      await loadServers();
    } catch (error) {
      console.error('Failed to scan server:', error);
    } finally {
      setBusyServerId(null);
    }
  };

  const handleSyncAll = async () => {
    try {
      setSyncingAll(true);
      await axios.post(`${API_BASE}/sync`);
    } catch (error) {
      console.error('Failed to sync:', error);
    } finally {
      setSyncingAll(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Paramètres</h1>
        <p className="page-subtitle">Personnalisez votre expérience</p>
      </div>

      <div style={{ ...cardStyle, marginTop: 0 }}>
        <div style={{ marginBottom: '25px' }}>
          <label style={labelStyle}>Thème</label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            style={inputStyle}
          >
            <option value="dark">Sombre</option>
            <option value="light">Clair</option>
            <option value="auto">Auto</option>
          </select>
        </div>

        <div style={{ marginBottom: '25px' }}>
          <label style={labelStyle}>Volume par défaut</label>
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

        <button onClick={handleSave} style={buttonStyle}>
          Enregistrer les paramètres
        </button>
      </div>

      <div style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ color: 'var(--primary)', margin: 0 }}>Serveurs</h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleSyncAll}
              disabled={syncingAll}
              style={{ ...secondaryButtonStyle, opacity: syncingAll ? 0.6 : 1 }}
            >
              {syncingAll ? 'Synchronisation...' : 'Synchroniser tout'}
            </button>
            <button
              onClick={() => {
                setShowAddForm(!showAddForm);
                resetForm();
              }}
              style={buttonStyle}
            >
              {showAddForm ? 'Annuler' : '+ Ajouter un serveur'}
            </button>
          </div>
        </div>

        {showAddForm && (
          <form
            onSubmit={handleAddServer}
            style={{
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '20px',
              marginBottom: '20px'
            }}
          >
            <div style={{ marginBottom: '15px' }}>
              <label style={labelStyle}>Type de serveur</label>
              <select
                value={formType}
                onChange={(e) => {
                  setFormType(e.target.value as ServerType);
                  setFormUrl('');
                }}
                style={inputStyle}
              >
                <option value="audiobookshelf">Audiobookshelf</option>
                <option value="plex">Plex</option>
                <option value="local">Dossier local</option>
              </select>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={labelStyle}>Nom</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Mon serveur"
                style={inputStyle}
              />
            </div>

            {formType === 'local' ? (
              <div style={{ marginBottom: '15px' }}>
                <label style={labelStyle}>Dossier</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    value={formUrl}
                    onChange={(e) => setFormUrl(e.target.value)}
                    placeholder="C:\Musique\Livres audio"
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <button type="button" onClick={handleBrowseFolder} style={secondaryButtonStyle}>
                    Parcourir
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ marginBottom: '15px' }}>
                <label style={labelStyle}>URL du serveur</label>
                <input
                  type="text"
                  value={formUrl}
                  onChange={(e) => setFormUrl(e.target.value)}
                  placeholder={formType === 'plex' ? 'http://192.168.1.100:32400' : 'http://votre-nas:13378'}
                  style={inputStyle}
                />
              </div>
            )}

            {formType === 'plex' && (
              <div style={{ marginBottom: '15px' }}>
                <label style={labelStyle}>Clé API (token)</label>
                <input
                  type="text"
                  value={formApiKey}
                  onChange={(e) => setFormApiKey(e.target.value)}
                  style={inputStyle}
                />
              </div>
            )}

            {formType === 'audiobookshelf' && (
              <>
                <div style={{ marginBottom: '15px' }}>
                  <label style={labelStyle}>Nom d'utilisateur</label>
                  <input
                    type="text"
                    value={formUsername}
                    onChange={(e) => setFormUsername(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div style={{ marginBottom: '15px' }}>
                  <label style={labelStyle}>Mot de passe</label>
                  <input
                    type="password"
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    style={inputStyle}
                  />
                </div>
              </>
            )}

            {formError && (
              <p style={{ color: '#ff6b6b', fontSize: '13px', marginBottom: '15px' }}>{formError}</p>
            )}

            <button type="submit" disabled={submitting} style={{ ...buttonStyle, opacity: submitting ? 0.6 : 1 }}>
              {submitting ? 'Connexion...' : 'Enregistrer'}
            </button>
          </form>
        )}

        {loadingServers ? (
          <p style={{ color: 'var(--text-secondary)' }}>Chargement...</p>
        ) : servers.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>Aucun serveur configuré</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {servers.map((server) => (
              <div
                key={server.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  padding: '12px 16px'
                }}
              >
                <div>
                  <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    {server.name}{' '}
                    <span style={{ color: 'var(--primary)', fontSize: '12px', fontWeight: 400 }}>
                      ({TYPE_LABELS[server.type]})
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                    {server.url}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                    {server.last_sync ? `Dernière sync : ${new Date(server.last_sync).toLocaleString('fr-FR')}` : 'Jamais synchronisé'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleScanServer(server.id)}
                    disabled={busyServerId === server.id}
                    style={{ ...secondaryButtonStyle, opacity: busyServerId === server.id ? 0.6 : 1 }}
                  >
                    Scanner
                  </button>
                  <button
                    onClick={() => handleDeleteServer(server.id, server.name)}
                    disabled={busyServerId === server.id}
                    style={{ ...secondaryButtonStyle, color: '#ff6b6b', opacity: busyServerId === server.id ? 0.6 : 1 }}
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={cardStyle}>
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
