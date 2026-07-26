import React, { useState, useEffect, useRef } from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import Player from './components/Player';
import HomePage from './pages/HomePage';
import ExplorePage from './pages/ExplorePage';
import BookDetailPage from './pages/BookDetailPage';
import AuthorPage from './pages/AuthorPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

// How long the backend can stay unreachable before we show an actual error
// screen. Below this, checks happen silently behind a plain loading screen -
// the backend is expected to take a moment to start up.
const ERROR_THRESHOLD_MS = 60000;
const CHECK_INTERVAL_MS = 1500;

const App: React.FC = () => {
  const [backendOnline, setBackendOnline] = useState(false);
  const [showError, setShowError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstFailureRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(API_BASE.replace('/api', '/health'), {
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
          setError(`Impossible de se connecter au serveur (${API_BASE.split('/').slice(-3).join('/')})`);
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
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Vérifiez que:</p>
            <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', textAlign: 'left' }}>
              <li>Le serveur Python est en cours d'exécution</li>
              <li>Aucun autre processus n'utilise le port 5000</li>
              <li>L'application réessayera la connexion automatiquement...</li>
            </ul>
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

    return (
      <HashRouter>
        <div className="app">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/explore" element={<ExplorePage />} />
              <Route path="/book/:id" element={<BookDetailPage />} />
              <Route path="/author/:name" element={<AuthorPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
          <Player />
        </div>
      </HashRouter>
    );
  };

  return (
    <div className="app-shell">
      <TitleBar />
      <div className="app-shell-body">{renderBody()}</div>
    </div>
  );
};

export default App;
