import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Player from './components/Player';
import HomePage from './pages/HomePage';
import ExplorePage from './pages/ExplorePage';
import BookDetailPage from './pages/BookDetailPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

const App: React.FC = () => {
  const [isDev, setIsDev] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check backend connectivity
    const checkBackend = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(API_BASE.replace('/api', '/health'), {
          signal: controller.signal
        });
        clearTimeout(timeout);

        if (response.ok) {
          setBackendOnline(true);
          setError(null);
        } else {
          setBackendOnline(false);
          setError('Backend non disponible');
        }
      } catch (err) {
        setBackendOnline(false);
        setError(`Impossible de se connecter au serveur (${API_BASE.split('/').slice(-3).join('/')})`);
      }
    };

    // Wait 2 seconds before first check (let backend start)
    const initialDelay = setTimeout(checkBackend, 2000);

    // Retry every 3 seconds if offline
    const interval = setInterval(checkBackend, 3000);

    return () => {
      clearTimeout(initialDelay);
      clearInterval(interval);
    };
  }, []);

  if (!backendOnline) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#0f0f0f',
        color: '#ffffff',
        fontFamily: 'system-ui'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔴</div>
        <h1>Serveur non disponible</h1>
        <p style={{ color: '#b0b0b0', marginBottom: '30px' }}>{error}</p>
        <p style={{ fontSize: '14px', color: '#888' }}>Vérifiez que:</p>
        <ul style={{ fontSize: '14px', color: '#888', textAlign: 'left' }}>
          <li>Le serveur Python est en cours d'exécution</li>
          <li>Aucun autre processus n'utilise le port 5000</li>
          <li>L'application réessayera la connexion automatiquement...</li>
        </ul>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/book/:id" element={<BookDetailPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
        <Player />
      </div>
    </BrowserRouter>
  );
};

export default App;
