import React from 'react';
import { useLocation, Routes, Route } from 'react-router-dom';
import HomePage from '../pages/HomePage';
import ExplorePage from '../pages/ExplorePage';
import BookDetailPage from '../pages/BookDetailPage';
import AuthorPage from '../pages/AuthorPage';
import HistoryPage from '../pages/HistoryPage';
import SettingsPage from '../pages/SettingsPage';

// Keying the wrapper by pathname makes React remount it on every navigation,
// which is what replays the CSS enter animation (.page-transition in
// App.css) each time instead of only on the very first page load.
const AnimatedRoutes: React.FC = () => {
  const location = useLocation();

  return (
    <div key={location.pathname} className="page-transition">
      <Routes location={location}>
        <Route path="/" element={<HomePage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/book/:id" element={<BookDetailPage />} />
        <Route path="/author/:name" element={<AuthorPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  );
};

export default AnimatedRoutes;
