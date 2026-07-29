import React, { useState, useEffect, useRef } from 'react';
import { HashRouter, useNavigate } from 'react-router-dom';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import Player from './components/Player';
import MiniPlayerView from './components/MiniPlayerView';
import CloseAppDialog from './components/CloseAppDialog';
import AnimatedRoutes from './components/AnimatedRoutes';
import { CloseBehavior } from './electron';
import { getApiBase, setApiBase } from './config';
import { isCapacitorPlatform } from './native/platform';
import { useExpandedPlayer } from './native/expandedPlayerStore';
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
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    if (!value.trim()) return;
    setApiBase(value);
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
const ERROR_THRESHOLD_MS = isCapacitorPlatform ? 0 : 60000;
const CHECK_INTERVAL_MS = 1500;

const App: React.FC = () => {
  const [backendOnline, setBackendOnline] = useState(false);
  const [showError, setShowError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const firstFailureRef = useRef<number | null>(null);
  const expandedPlayer = useExpandedPlayer();

  useEffect(() => {
    if (isMiniWindow) return;
    window.electron?.onCloseRequested(() => setShowCloseDialog(true));
  }, []);

  const handleCloseChoice = (action: CloseBehavior, remember: boolean) => {
    setShowCloseDialog(false);
    window.electron?.respondToClose(action, remember);
  };

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      const apiBase = getApiBase();
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(apiBase.replace('/api', '/health'), {
          signal: controller.signal
        });
        clearTimeout(timeout);

        if (cancelled) return;

        if (response.ok) {
          firstFailureRef.current = null;
          setBackendOnline(true);
          setShowError(false);
          setError(null);
        } else {
          throw new Error('Backend non disponible');
        }
      } catch (err) {
        if (cancelled) return;

        if (firstFailureRef.current === null) {
          firstFailureRef.current = Date.now();
        }

        setBackendOnline(false);
        if (Date.now() - firstFailureRef.current >= ERROR_THRESHOLD_MS) {
          setError(`Impossible de se connecter au serveur (${apiBase.split('/').slice(-3).join('/')})`);
          setShowError(true);
        }
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, CHECK_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

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
            <h1>Serveur non disponible</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>{error}</p>
            {isCapacitorPlatform ? (
              <ServerConfigForm onSaved={() => {
                firstFailureRef.current = null;
                setShowError(false);
              }} />
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
        <div className={`app ${isCapacitorPlatform && expandedPlayer ? 'mobile-player-expanded' : ''}`}>
          <Sidebar />
          <main className="main-content">
            <AnimatedRoutes />
          </main>
          <Player />
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
