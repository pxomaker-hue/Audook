import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, RotateCcw, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import { CloseBehavior } from '../electron';
import EqualizerSettings from '../components/EqualizerSettings';
import { getApiBase, setApiBase, resetApiBase } from '../config';

type ServerType = 'plex' | 'audiobookshelf' | 'local';

interface ServerEntry {
  id: string;
  type: ServerType;
  name: string;
  url: string;
  remote_url: string | null;
  use_remote: boolean;
  hidden: boolean;
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
  borderRadius: 'var(--radius-md)',
  boxShadow: 'var(--shadow-pop)',
  padding: '30px',
  maxWidth: '600px',
  marginTop: '30px'
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '11px 16px',
  backgroundColor: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  borderRadius: '999px',
  fontFamily: 'inherit',
  fontSize: '14px'
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '8px',
  color: 'var(--text-primary)',
  fontSize: '13px',
  fontWeight: 600
};

const buttonStyle: React.CSSProperties = {
  background: 'var(--primary)',
  color: 'var(--secondary)',
  border: 'none',
  padding: '11px 22px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 700,
  transition: 'transform 0.15s'
};

const secondaryButtonStyle: React.CSSProperties = {
  background: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  padding: '9px 16px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 600,
  transition: 'transform 0.15s'
};

const iconButtonStyle: React.CSSProperties = {
  ...secondaryButtonStyle,
  padding: '9px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const SettingsPage: React.FC = () => {
  const [theme, setTheme] = useState('dark');
  const [volume, setVolume] = useState(80);
  const [autoSync, setAutoSync] = useState(true);
  const [closeBehavior, setCloseBehaviorState] = useState<CloseBehavior>('ask');

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
  const [resettingProgress, setResettingProgress] = useState(false);
  const [remoteUrlDrafts, setRemoteUrlDrafts] = useState<Record<string, string>>({});
  const [savingRemoteId, setSavingRemoteId] = useState<string | null>(null);
  const [togglingHiddenId, setTogglingHiddenId] = useState<string | null>(null);
  const [serverUrlDraft, setServerUrlDraft] = useState(getApiBase());
  const [serverUrlSaved, setServerUrlSaved] = useState(false);

  const loadServers = useCallback(async () => {
    try {
      setLoadingServers(true);
      const response = await axios.get(`${getApiBase()}/servers`);
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

  useEffect(() => {
    window.electron?.getCloseBehavior().then((value) => {
      if (value) setCloseBehaviorState(value);
    });
  }, []);

  const handleCloseBehaviorChange = (value: CloseBehavior) => {
    setCloseBehaviorState(value);
    window.electron?.setCloseBehavior(value);
  };

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
      await axios.post(`${getApiBase()}/servers`, payload);
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
      await axios.delete(`${getApiBase()}/servers/${id}`);
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
      await axios.post(`${getApiBase()}/servers/${id}/scan`);
      await loadServers();
    } catch (error) {
      console.error('Failed to scan server:', error);
    } finally {
      setBusyServerId(null);
    }
  };

  const handleSaveRemoteUrl = async (id: string) => {
    const remoteUrl = (remoteUrlDrafts[id] ?? '').trim();
    try {
      setSavingRemoteId(id);
      await axios.post(`${getApiBase()}/servers/${id}/remote-access`, { remote_url: remoteUrl || null });
      await loadServers();
    } catch (error) {
      console.error('Failed to save remote URL:', error);
    } finally {
      setSavingRemoteId(null);
    }
  };

  const handleToggleRemote = async (server: ServerEntry) => {
    try {
      setSavingRemoteId(server.id);
      await axios.post(`${getApiBase()}/servers/${server.id}/remote-access`, { use_remote: !server.use_remote });
      await loadServers();
    } catch (error) {
      console.error('Failed to toggle remote access:', error);
    } finally {
      setSavingRemoteId(null);
    }
  };

  const handleToggleHidden = async (server: ServerEntry) => {
    try {
      setTogglingHiddenId(server.id);
      await axios.post(`${getApiBase()}/servers/${server.id}/hidden`, { hidden: !server.hidden });
      await loadServers();
    } catch (error) {
      console.error('Failed to toggle server visibility:', error);
    } finally {
      setTogglingHiddenId(null);
    }
  };

  const handleSyncAll = async () => {
    if (syncingAll) return;
    try {
      setSyncingAll(true);
      await axios.post(`${getApiBase()}/sync`);

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${getApiBase()}/sync/status`);
          if (!statusRes.data.syncing) {
            clearInterval(pollInterval);
            setSyncingAll(false);
            await loadServers();
          }
        } catch (error) {
          console.error('Failed to poll sync status:', error);
          clearInterval(pollInterval);
          setSyncingAll(false);
        }
      }, 800);
    } catch (error) {
      console.error('Failed to sync:', error);
      setSyncingAll(false);
    }
  };

  const handleSaveServerUrl = () => {
    const trimmed = serverUrlDraft.trim();
    if (!trimmed) return;
    setApiBase(trimmed);
    setServerUrlDraft(getApiBase());
    setServerUrlSaved(true);
    setTimeout(() => setServerUrlSaved(false), 2000);
  };

  const handleResetServerUrl = () => {
    resetApiBase();
    setServerUrlDraft(getApiBase());
    setServerUrlSaved(true);
    setTimeout(() => setServerUrlSaved(false), 2000);
  };

  const handleResetAllProgress = async () => {
    if (!window.confirm("Réinitialiser toute la progression de lecture ? Tous les livres seront retirés de \"Reprendre l'écoute\".")) return;
    try {
      setResettingProgress(true);
      await axios.delete(`${getApiBase()}/progress`);
    } catch (error) {
      console.error('Failed to reset progress:', error);
    } finally {
      setResettingProgress(false);
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

        <button className="cta-button" onClick={handleSave} style={buttonStyle}>
          Enregistrer les paramètres
        </button>
      </div>

      {window.electron && (
        <div style={cardStyle}>
          <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>Fermeture de l'application</h2>
          <label style={labelStyle}>Quand je clique sur fermer</label>
          <select
            value={closeBehavior}
            onChange={(e) => handleCloseBehaviorChange(e.target.value as CloseBehavior)}
            style={inputStyle}
          >
            <option value="ask">Toujours demander</option>
            <option value="tray">Réduire dans la barre système</option>
            <option value="quit">Fermer l'application</option>
          </select>
        </div>
      )}

      <div style={cardStyle}>
        <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>Connexion au backend</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '15px' }}>
          Adresse du serveur Audook auquel se connecter. Utile pour pointer cette instance vers un backend hébergé sur votre NAS (ex: <code>http://192.168.1.50:5000/api</code>).
        </p>
        <label style={labelStyle}>Serveur</label>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={serverUrlDraft}
            onChange={(e) => setServerUrlDraft(e.target.value)}
            placeholder="http://localhost:5000/api"
            style={{ ...inputStyle, flex: 1, minWidth: '260px' }}
          />
          <button type="button" className="cta-button" onClick={handleSaveServerUrl} style={buttonStyle}>
            Enregistrer
          </button>
          <button type="button" className="cta-button" onClick={handleResetServerUrl} style={secondaryButtonStyle}>
            Réinitialiser
          </button>
        </div>
        {serverUrlSaved && (
          <p style={{ color: 'var(--primary)', fontSize: '12px', marginTop: '10px' }}>Adresse enregistrée.</p>
        )}
      </div>

      <div style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ color: 'var(--primary)', margin: 0 }}>Serveurs</h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleSyncAll}
              disabled={syncingAll}
              className="cta-button"
              style={{ ...secondaryButtonStyle, display: 'flex', alignItems: 'center', gap: '8px', opacity: syncingAll ? 0.7 : 1 }}
            >
              <RefreshCw size={14} className={syncingAll ? 'spin' : ''} />
              {syncingAll ? 'Synchronisation...' : 'Synchroniser tout'}
            </button>
            <button
              onClick={() => {
                setShowAddForm(!showAddForm);
                resetForm();
              }}
              className="cta-button"
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
              backgroundColor: 'var(--surface-muted)',
              borderRadius: 'var(--radius-sm)',
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
                  <button type="button" className="cta-button" onClick={handleBrowseFolder} style={secondaryButtonStyle}>
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

            <button type="submit" className="cta-button" disabled={submitting} style={{ ...buttonStyle, opacity: submitting ? 0.6 : 1 }}>
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
                  backgroundColor: 'var(--surface-muted)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px 18px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                      {server.name}{' '}
                      <span style={{ color: 'var(--primary)', fontSize: '12px', fontWeight: 400 }}>
                        ({TYPE_LABELS[server.type]})
                      </span>
                      {server.hidden && (
                        <span style={{ color: 'var(--text-tertiary)', fontSize: '12px', fontWeight: 400 }}> · masqué de la bibliothèque</span>
                      )}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                      {server.use_remote && server.remote_url ? server.remote_url : server.url}
                      {server.use_remote && server.remote_url && (
                        <span style={{ color: 'var(--primary)', fontWeight: 600 }}> (distant)</span>
                      )}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                      {server.last_sync ? `Dernière sync : ${new Date(server.last_sync).toLocaleString('fr-FR')}` : 'Jamais synchronisé'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => handleToggleHidden(server)}
                      disabled={togglingHiddenId === server.id}
                      className="cta-button"
                      title={server.hidden ? 'Afficher dans la bibliothèque' : 'Masquer de la bibliothèque'}
                      style={{
                        ...iconButtonStyle,
                        opacity: togglingHiddenId === server.id ? 0.6 : 1,
                        color: server.hidden ? 'var(--text-tertiary)' : 'var(--text-primary)'
                      }}
                    >
                      {server.hidden ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                    <button
                      onClick={() => handleScanServer(server.id)}
                      disabled={busyServerId === server.id}
                      className="cta-button"
                      style={{ ...secondaryButtonStyle, opacity: busyServerId === server.id ? 0.6 : 1 }}
                    >
                      Scanner
                    </button>
                    <button
                      onClick={() => handleDeleteServer(server.id, server.name)}
                      disabled={busyServerId === server.id}
                      className="cta-button"
                      style={{ ...secondaryButtonStyle, color: '#ff6b6b', opacity: busyServerId === server.id ? 0.6 : 1 }}
                    >
                      Supprimer
                    </button>
                  </div>
                </div>

                {server.type === 'audiobookshelf' && (
                  <div
                    style={{
                      marginTop: '12px',
                      paddingTop: '12px',
                      borderTop: '1px solid var(--border)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      flexWrap: 'wrap'
                    }}
                  >
                    <input
                      type="text"
                      value={remoteUrlDrafts[server.id] ?? server.remote_url ?? ''}
                      onChange={(e) => setRemoteUrlDrafts(prev => ({ ...prev, [server.id]: e.target.value }))}
                      onBlur={() => {
                        if ((remoteUrlDrafts[server.id] ?? server.remote_url ?? '') !== (server.remote_url ?? '')) {
                          handleSaveRemoteUrl(server.id);
                        }
                      }}
                      placeholder="URL distante (ex: https://abs.mondomaine.com)"
                      style={{ ...inputStyle, flex: 1, minWidth: '220px', padding: '8px 14px', fontSize: '12px' }}
                    />
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                        cursor: server.remote_url ? 'pointer' : 'not-allowed',
                        opacity: server.remote_url ? 1 : 0.5,
                        whiteSpace: 'nowrap'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={server.use_remote}
                        disabled={!server.remote_url || savingRemoteId === server.id}
                        onChange={() => handleToggleRemote(server)}
                        style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                      />
                      Accès distant
                    </label>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <EqualizerSettings />

      <div style={cardStyle}>
        <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>Maintenance</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '15px' }}>
          Retire tous les livres de la section "Reprendre l'écoute" en réinitialisant leur progression de lecture.
        </p>
        <button
          className="cta-button"
          onClick={handleResetAllProgress}
          disabled={resettingProgress}
          style={{
            background: 'var(--surface-muted)',
            color: 'var(--text-primary)',
            border: 'none',
            padding: '10px 18px',
            borderRadius: '999px',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: resettingProgress ? 0.6 : 1
          }}
        >
          <RotateCcw size={14} /> Réinitialiser toutes les progressions
        </button>
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
