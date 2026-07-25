import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Compass, History, Settings } from 'lucide-react';

const Sidebar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">🎧 Audook</div>
      </div>
      <nav className="sidebar-nav">
        <Link
          to="/"
          className={`nav-item ${isActive('/') ? 'active' : ''}`}
        >
          <Home size={20} />
          <span>Bibliothèque</span>
        </Link>
        <Link
          to="/explore"
          className={`nav-item ${isActive('/explore') ? 'active' : ''}`}
        >
          <Compass size={20} />
          <span>Découvrir</span>
        </Link>
        <Link
          to="/history"
          className={`nav-item ${isActive('/history') ? 'active' : ''}`}
        >
          <History size={20} />
          <span>Historique</span>
        </Link>
        <Link
          to="/settings"
          className={`nav-item ${isActive('/settings') ? 'active' : ''}`}
        >
          <Settings size={20} />
          <span>Paramètres</span>
        </Link>
      </nav>
    </div>
  );
};

export default Sidebar;
