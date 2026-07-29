import React, { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutGrid, Compass, History, Settings, Headphones, Library } from 'lucide-react';
import { expandedPlayerStore, useExpandedPlayer } from '../native/expandedPlayerStore';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const expanded = useExpandedPlayer();
  const firstRender = useRef(true);

  const isActive = (path: string) => location.pathname === path;

  // A nav tap always means "leave the full-screen player" - collapse it back
  // to the normal library view. Skip the very first mount so this doesn't
  // fire on initial load.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    expandedPlayerStore.setExpanded(false);
  }, [location.pathname]);

  return (
    <div className={`sidebar ${expanded ? 'sidebar-bottom' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Headphones size={18} />
        </div>
      </div>
      <nav className="sidebar-nav">
        <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`} title="Bibliothèque">
          <LayoutGrid size={20} />
        </Link>
        <Link to="/collections" className={`nav-item ${isActive('/collections') ? 'active' : ''}`} title="Collections">
          <Library size={20} />
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
