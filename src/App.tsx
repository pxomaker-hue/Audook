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

const App: React.FC = () => {
  const [isDev, setIsDev] = useState(false);

  useEffect(() => {
    // Get app config from Electron
    const appConfig = window.electron?.getAppConfig?.();
    if (appConfig) {
      appConfig.then((config: any) => {
        setIsDev(config.isDev);
      });
    }
  }, []);

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
