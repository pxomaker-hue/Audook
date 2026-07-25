import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutGrid, Compass, History, Settings, Headphones } from 'lucide-react';

const Sidebar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Headphones size={18} />
        </div>
      </div>
      <nav className="sidebar-nav">
        <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`} title="Bibliothèque">
          <LayoutGrid size={20} />
        </Link>
        <Link to="/explore" className={`nav-item ${isActive('/explore') ? 'active' : ''}`} title="Découvrir">
          <Compass size={20} />
        </Link>
        <Link to="/history" className={`nav-item ${isActive('/history') ? 'active' : ''}`} title="Historique">
          <History size={20} />
        </Link>
        <div className="sidebar-spacer" />
        <Link to="/settings" className={`nav-item ${isActive('/settings') ? 'active' : ''}`} title="Paramètres">
          <Settings size={20} />
        </Link>
      </nav>
    </div>
  );
};

export default Sidebar;
