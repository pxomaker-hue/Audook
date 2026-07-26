import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Play, RefreshCw, User } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

interface Book {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
  duration: number;
  source: string;
  progress_percent: number;
  current_chapter_title: string | null;
  author_photo: string | null;
}

interface ServerEntry {
  id: string;
  type: 'plex' | 'audiobookshelf' | 'local';
  name: string;
}

const SOURCE_LABELS: Record<string, string> = {
  audiobookshelf: 'Audiobookshelf',
  plex: 'Plex',
  local: 'Local'
};

const AVATAR_COLORS = ['#ffc629', '#17161b', '#c3c2c9', '#f4f4f2'];

const initials = (name: string) =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase())
    .join('');

const formatDuration = (seconds: number) => {
  if (!seconds) return '--';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}` : `${minutes}min`;
};

const HomePage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [servers, setServers] = useState<ServerEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSource, setActiveSource] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchAll = async () => {
    try {
      const [booksRes, serversRes] = await Promise.all([
        axios.get(`${API_BASE}/books`),
        axios.get(`${API_BASE}/servers`)
      ]);
      setBooks(booksRes.data);
      setServers(serversRes.data);
    } catch (error) {
      console.error('Failed to fetch library:', error);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));
  }, []);

  const availableSources = useMemo(
    () => Array.from(new Set(servers.map(s => s.type))),
    [servers]
  );

  const filteredBooks = useMemo(() => {
    let list = books;
    if (activeSource !== 'all') {
      list = list.filter(b => b.source === activeSource);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        b => b.title.toLowerCase().includes(q) || b.author.toLowerCase().includes(q)
      );
    }
    return list;
  }, [books, activeSource, searchQuery]);

  const topAuthors = useMemo(() => {
    const counts = new Map<string, number>();
    const photos = new Map<string, string>();
    books.forEach(b => {
      counts.set(b.author, (counts.get(b.author) || 0) + 1);
      if (b.author_photo && !photos.has(b.author)) {
        photos.set(b.author, b.author_photo);
      }
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([author, count]) => ({ author, count, photo: photos.get(author) || null }));
  }, [books]);

  const handlePlayBook = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    try {
      await axios.post(`${API_BASE}/player/play`, { book_id: bookId });
    } catch (error) {
      console.error('Failed to play book:', error);
    }
  };

  const handleSync = async () => {
    if (syncing) return;
    try {
      setSyncing(true);
      setSyncMessage('Synchronisation...');
      await axios.post(`${API_BASE}/sync`);

      // The sync runs in a background thread on the backend; poll its status
      // until it's done, then refresh the library so new/updated books show up.
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${API_BASE}/sync/status`);
          if (statusRes.data.message) {
            setSyncMessage(statusRes.data.message);
          }
          if (!statusRes.data.syncing) {
            clearInterval(pollInterval);
            setSyncing(false);
            await fetchAll();
            setTimeout(() => setSyncMessage(null), 3000);
          }
        } catch (error) {
          console.error('Failed to poll sync status:', error);
          clearInterval(pollInterval);
          setSyncing(false);
        }
      }, 800);
    } catch (error) {
      console.error('Failed to sync:', error);
      setSyncing(false);
      setSyncMessage('Échec de la synchronisation');
      setTimeout(() => setSyncMessage(null), 3000);
    }
  };

  // "In progress" = has been started but not finished. Shown bigger, above the
  // full library grid, and excluded from it to avoid showing the same book twice.
  const inProgressBooks = useMemo(
    () => books.filter(b => b.progress_percent > 0 && b.progress_percent < 100),
    [books]
  );
  const inProgressIds = useMemo(() => new Set(inProgressBooks.map(b => b.id)), [inProgressBooks]);
  const libraryBooks = filteredBooks.filter(b => !inProgressIds.has(b.id));

  const renderBookCard = (book: Book) => (
    <div key={book.id} className="book-card" onClick={() => navigate(`/book/${book.id}`)}>
      <div className="book-card-cover">
        {book.cover_url ? (
          <img src={book.cover_url} alt={book.title} />
        ) : (
          <span>📚</span>
        )}
        <span className="book-card-badge">{formatDuration(book.duration)}</span>
        <div className="book-card-overlay">
          <button className="play-button" onClick={(e) => handlePlayBook(e, book.id)} title="Lire">
            <Play size={18} fill="currentColor" />
          </button>
        </div>
        {book.progress_percent > 0 && (
          <div className="book-card-progress-bar">
            <div className="book-card-progress-fill" style={{ width: `${book.progress_percent}%` }} />
          </div>
        )}
      </div>
      <div className="book-card-info">
        <div className="book-card-title">{book.title}</div>
        <div className="book-card-author">{book.author}</div>
        {book.current_chapter_title && (
          <div className="book-card-chapter">{book.current_chapter_title}</div>
        )}
      </div>
    </div>
  );

  return (
    <div className="page-content">
      <div className="top-bar">
        <div className="category-pills">
          <button
            className={`category-pill ${activeSource === 'all' ? 'active' : ''}`}
            onClick={() => setActiveSource('all')}
          >
            Tous
          </button>
          {availableSources.map(source => (
            <button
              key={source}
              className={`category-pill ${activeSource === source ? 'active' : ''}`}
              onClick={() => setActiveSource(source)}
            >
              {SOURCE_LABELS[source] || source}
            </button>
          ))}
        </div>

        <div className="top-bar-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Rechercher un livre ou un auteur..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <button className="top-bar-icon-button" onClick={() => navigate('/settings')} title="Paramètres">
          <User size={18} />
        </button>
        <button
          className="top-bar-icon-button dark"
          onClick={handleSync}
          title="Synchroniser les serveurs"
          disabled={syncing}
        >
          <RefreshCw size={16} className={syncing ? 'spin' : ''} />
          {servers.length > 0 && !syncing && <span className="dot" />}
        </button>
      </div>

      {syncMessage && <div className="sync-toast">{syncMessage}</div>}

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement des audiolivres...
        </div>
      ) : books.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucun audiolivre. Ajoutez un serveur dans les Paramètres pour commencer.
        </div>
      ) : (
        <>
          {inProgressBooks.length > 0 && (
            <>
              <h2 className="section-title">Reprendre l'écoute</h2>
              <div className="books-grid books-grid--featured">
                {inProgressBooks.map(renderBookCard)}
              </div>
            </>
          )}

          {topAuthors.length > 0 && (
            <>
              <h2 className="section-title">Tri par auteurs</h2>
              <div className="authors-grid">
                {topAuthors.map(({ author, count, photo }, i) => (
                  <div
                    key={author}
                    className="author-row"
                    onClick={() => navigate(`/author/${encodeURIComponent(author)}`)}
                  >
                    <div
                      className="author-avatar"
                      style={{ backgroundColor: photo ? undefined : AVATAR_COLORS[i % AVATAR_COLORS.length] }}
                    >
                      {photo ? <img src={photo} alt={author} /> : (initials(author) || '?')}
                    </div>
                    <div className="author-name">{author}</div>
                    <div className="author-count">{count}</div>
                  </div>
                ))}
              </div>
            </>
          )}

          <h2 className="section-title">Toute la bibliothèque</h2>
          {libraryBooks.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', padding: '20px 0' }}>
              Aucun autre audiolivre.
            </div>
          ) : (
            <div className="books-grid">
              {libraryBooks.map(renderBookCard)}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default HomePage;
