import React, { useState, useEffect } from 'react';
import { HashRouter, useNavigate } from 'react-router-dom';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import Player from './components/Player';
import MiniPlayerView from './components/MiniPlayerView';
import CloseAppDialog from './components/CloseAppDialog';
import AnimatedRoutes from './components/AnimatedRoutes';
import { CloseBehavior } from './electron';
import { getApiBase, getApiToken, setApiBase, setApiToken } from './config';
import { useBackendConnection } from './hooks/useBackendConnection';
import { isCapacitorPlatform } from './native/platform';
import { useExpandedPlayer } from './native/expandedPlayerStore';
import { checkForUpdate } from './updates';
import './App.css';

// The detached mini-player (electron/main.js createMiniWindow) loads this
// same app at the '#/mini' hash route - render just the player for it,
// skipping the title bar / sidebar / routed pages entirely.
const isMiniWindow = window.location.hash.startsWith('#/mini');

// On desktop, Electron starts the backend locally so it's reachable within
// a second or two - the loading/error screens below are purely transitional.
// On mobile there is no local backend: the default API base (localhost)
// can never succeed until the user enters their NAS's LAN address, so we
// need an escape hatch to configure it before a connection ever succeeds.
const ServerConfigForm: React.FC<{ onSaved: () => void }> = ({ onSaved }) => {
  const [value, setValue] = useState(getApiBase());
  const [token, setToken] = useState(getApiToken());
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    if (!value.trim()) return;
    setApiBase(value);
    setApiToken(token);
    setSaved(true);
    onSaved();
  };

  return (
    <div style={{ marginTop: '20px', width: '100%', maxWidth: '320px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <label style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Adresse du serveur (ex: http://192.168.1.200:5000/api)</label>
      <input
        type="text"
        value={value}
        onChange={(e) => { setValue(e.target.value); setSaved(false); }}
        placeholder="http://192.168.1.200:5000/api"
        style={{
          padding: '10px',
          borderRadius: '6px',
          border: '1px solid var(--border, #444)',
          backgroundColor: 'var(--surface, #222)',
          color: 'var(--text-primary)'
        }}
      />
      <label style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Jeton d'accès (laisser vide si le serveur n'en demande pas)</label>
      <input
        type="password"
        value={token}
        onChange={(e) => { setToken(e.target.value); setSaved(false); }}
        placeholder="AUDOOK_API_TOKEN du serveur"
        autoComplete="off"
        style={{
          padding: '10px',
          borderRadius: '6px',
          border: '1px solid var(--border, #444)',
          backgroundColor: 'var(--surface, #222)',
          color: 'var(--text-primary)'
        }}
      />
      <button
        onClick={handleSave}
        style={{
          padding: '10px',
          borderRadius: '6px',
          border: 'none',
          backgroundColor: 'var(--primary)',
          color: '#fff',
          cursor: 'pointer'
        }}
      >
        Enregistrer et réessayer
      </button>
      {saved && <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Nouvelle tentative de connexion...</p>}
    </div>
  );
};

// Listens for the mini-player window asking the main window to open a
// book's page (see electron/preload.js onNavigateToBook / electron/main.js
// mini-player:open-book) - has to live inside <HashRouter> to get a router
// to navigate with, which is why it's a separate component rather than
// just an effect in App itself.
const UpdateBanner: React.FC = () => {
  const [latest, setLatest] = useState('');
  const navigate = useNavigate();
  useEffect(() => {
    checkForUpdate().then((u) => u.available && setLatest(u.latest)).catch(() => {});
  }, []);
  if (!latest) return null;
  return (
    <div role="status" style={{ position: 'fixed', bottom: 8, left: '50%', transform: 'translateX(-50%)', zIndex: 1000, padding: '6px 14px', borderRadius: '999px', fontSize: '12px', backgroundColor: 'var(--primary)', color: '#fff', display: 'flex', gap: '10px', alignItems: 'center' }}>
      Audook v{latest} est disponible
      <button onClick={() => { navigate('/settings'); setLatest(''); }} style={{ background: 'rgba(255,255,255,.25)', color: '#fff', border: 'none', borderRadius: '999px', padding: '2px 10px', cursor: 'pointer' }}>Voir</button>
      <button aria-label="Fermer" onClick={() => setLatest('')} style={{ background: 'none', color: '#fff', border: 'none', cursor: 'pointer' }}>×</button>
    </div>
  );
};

const NavigateToBookListener: React.FC = () => {
  const navigate = useNavigate();
  useEffect(() => {
    window.electron?.onNavigateToBook((bookId: string) => navigate(`/book/${bookId}`));
  }, [navigate]);
  return null;
};

// How long the backend can stay unreachable before we show an actual error
// screen. Below this, checks happen silently behind a plain loading screen -
// the backend is expected to take a moment to start up. On mobile there's
// no local backend to wait for, so surface the config form immediately
// instead of making the user stare at a spinner for a minute first.
const ERROR_THRESHOLD_MS = isCapacitorPlatform ? 8000 : 60000;

const App: React.FC = () => {
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const { backendOnline, authRequired, showError, reconnecting, resetFailures } = useBackendConnection(ERROR_THRESHOLD_MS);
  const error = authRequired
    ? "Accès refusé : jeton d'accès manquant ou invalide."
    : `Impossible de se connecter au serveur (${getApiBase().split('/').slice(-3).join('/')})`;
  const expandedPlayer = useExpandedPlayer();

  useEffect(() => {
    if (isMiniWindow) return;
    window.electron?.onCloseRequested(() => setShowCloseDialog(true));
  }, []);

  const handleCloseChoice = (action: CloseBehavior, remember: boolean) => {
    setShowCloseDialog(false);
    window.electron?.respondToClose(action, remember);
  };

  const renderBody = () => {
    if (!backendOnline) {
      if (showError) {
        return (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            backgroundColor: 'var(--background)',
            color: 'var(--text-primary)',
            fontFamily: 'inherit'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔴</div>
            <h1>{authRequired ? 'Accès refusé' : 'Serveur non disponible'}</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>{error}</p>
            {isCapacitorPlatform || authRequired ? (
              <ServerConfigForm onSaved={resetFailures} />
            ) : (
              <>
                <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Vérifiez que:</p>
                <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', textAlign: 'left' }}>
                  <li>Le serveur Python est en cours d'exécution</li>
                  <li>Aucun autre processus n'utilise le port 5000</li>
                  <li>L'application réessayera la connexion automatiquement...</li>
                </ul>
              </>
            )}
          </div>
        );
      }

      // Silent loading state: the backend is expected to take a moment to
      // start up, so no error is shown until ERROR_THRESHOLD_MS has elapsed.
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          backgroundColor: 'var(--background)',
          gap: '20px'
        }}>
          <div className="app-boot-spinner" />
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Démarrage d'Audook...</p>
        </div>
      );
    }

    if (isMiniWindow) {
      return <MiniPlayerView />;
    }

    return (
      <HashRouter>
        <NavigateToBookListener />
        <UpdateBanner />
        <div className={`app ${isCapacitorPlatform && expandedPlayer ? 'mobile-player-expanded' : ''}`}>
          <Sidebar />
          <main className="main-content">
            <AnimatedRoutes />
          </main>
          <Player />
          {reconnecting && (
            <div role="status" style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000, padding: '4px 8px', textAlign: 'center', fontSize: '12px', backgroundColor: 'var(--primary)', color: '#fff' }}>
              Connexion au serveur instable, nouvelle tentative…
            </div>
          )}
        </div>
      </HashRouter>
    );
  };

  return (
    <div className={`app-shell ${isMiniWindow ? 'mini-window' : ''}`}>
      {!isMiniWindow && <TitleBar />}
      <div className="app-shell-body">{renderBody()}</div>
      {!isMiniWindow && <CloseAppDialog open={showCloseDialog} onChoice={handleCloseChoice} />}
    </div>
  );
};

export default App;
