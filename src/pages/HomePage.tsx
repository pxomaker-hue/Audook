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
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const [booksRes, serversRes] = await Promise.all([
          axios.get(`${API_BASE}/books`),
          axios.get(`${API_BASE}/servers`)
        ]);
        setBooks(booksRes.data);
        setServers(serversRes.data);
      } catch (error) {
        console.error('Failed to fetch library:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
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
    books.forEach(b => counts.set(b.author, (counts.get(b.author) || 0) + 1));
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([author, count]) => ({ author, count }));
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
    try {
      setSyncing(true);
      await axios.post(`${API_BASE}/sync`);
    } catch (error) {
      console.error('Failed to sync:', error);
    } finally {
      setTimeout(() => setSyncing(false), 1200);
    }
  };

  const myBooks = books.slice(0, 3);
  const libraryBooks = filteredBooks.slice(3);

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
        >
          <RefreshCw size={16} className={syncing ? 'spin' : ''} />
          {servers.length > 0 && <span className="dot" />}
        </button>
      </div>

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
          {myBooks.length > 0 && (
            <>
              <h2 className="section-title">Mes livres</h2>
              <div className="myrow">
                {myBooks.map(book => (
                  <div key={book.id} className="myrow-card" onClick={() => navigate(`/book/${book.id}`)}>
                    <div className="myrow-cover">
                      {book.cover_url ? (
                        <img src={book.cover_url} alt={book.title} />
                      ) : (
                        <div
                          style={{
                            width: '100%',
                            height: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '20px'
                          }}
                        >
                          📚
                        </div>
                      )}
                    </div>
                    <div className="myrow-info">
                      <div className="myrow-title">{book.title}</div>
                      <div className="myrow-author">{book.author}</div>
                      <button className="play-button" onClick={(e) => handlePlayBook(e, book.id)} title="Lire">
                        <Play size={16} fill="currentColor" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {topAuthors.length > 0 && (
            <>
              <h2 className="section-title">Meilleurs auteurs</h2>
              <div className="authors-grid">
                {topAuthors.map(({ author, count }, i) => (
                  <div key={author} className="author-row">
                    <div
                      className="author-avatar"
                      style={{ backgroundColor: AVATAR_COLORS[i % AVATAR_COLORS.length] }}
                    >
                      {initials(author) || '?'}
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
              {libraryBooks.map(book => (
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
                  </div>
                  <div className="book-card-info">
                    <div className="book-card-title">{book.title}</div>
                    <div className="book-card-author">{book.author}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default HomePage;
