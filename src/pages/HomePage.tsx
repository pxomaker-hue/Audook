import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Play, RefreshCw, User, X, Bookmark, ChevronDown, Check } from 'lucide-react';
import axios from 'axios';
import ConfirmDialog from '../components/ConfirmDialog';
import { getApiBase } from '../config';
import CoverImage from '../components/CoverImage';
import { isCapacitorPlatform } from '../native/platform';
import { mobilePlayerStore } from '../native/mobilePlayerStore';

const SORT_STORAGE_KEY = 'audook_library_sort';

interface Book {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
  duration: number;
  source: string;
  series: string | null;
  series_sequence: string | number | null;
  genre: string[];
  progress_percent: number;
  current_chapter_title: string | null;
  is_finished: boolean;
  has_bookmark: boolean;
  author_photo: string | null;
}

interface ServerEntry {
  id: string;
  type: 'plex' | 'audiobookshelf' | 'local';
  name: string;
}

interface CollectionEntry {
  id: string;
  name: string;
  book_ids: string[];
}

type SortMode = 'series' | 'alphabetical' | 'author' | 'genre' | 'collection' | 'progress' | 'bookmark';

const SORT_LABELS: Record<SortMode, string> = {
  series: 'Par séries',
  alphabetical: 'Ordre alphabétique',
  author: 'Par auteurs',
  genre: 'Par genre',
  collection: 'Par collection',
  progress: 'Par progression',
  bookmark: 'Marque-pages'
};

const NO_COLLECTION_LABEL = 'Sans collection';

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

// The sort key used for "Par séries": the series name when set, otherwise a
// single shared "Sans série" bucket - grouping standalone books one-by-one
// under their own author name looked like a broken/author sort instead of a
// series sort, so every standalone book now lands in the same bucket.
const NO_SERIES_LABEL = 'Sans série';
const seriesGroupKey = (book: Book) => (book.series && book.series.trim()) || NO_SERIES_LABEL;

// Same grouping idea for "Par genre" - the book's first genre tag, or a
// fallback bucket for books with no genre data at all.
const genreGroupKey = (book: Book) => (book.genre && book.genre.length > 0 ? book.genre[0] : 'Genre inconnu');

const HomePage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [servers, setServers] = useState<ServerEntry[]>([]);
  const [collections, setCollections] = useState<CollectionEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSource, setActiveSource] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>(() => {
    const saved = localStorage.getItem(SORT_STORAGE_KEY);
    return (saved as SortMode) || 'series';
  });
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [confirmDismissId, setConfirmDismissId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    localStorage.setItem(SORT_STORAGE_KEY, sortMode);
  }, [sortMode]);

  const fetchAll = async () => {
    try {
      const [booksRes, serversRes, collectionsRes] = await Promise.all([
        axios.get(`${getApiBase()}/books`),
        axios.get(`${getApiBase()}/servers`),
        axios.get(`${getApiBase()}/collections`)
      ]);
      // The NAS backend has been observed returning its JSON body as a
      // plain string instead of a parsed array in some WebView/network
      // configurations - guard against that instead of crashing every
      // .map()/.filter() downstream.
      setBooks(Array.isArray(booksRes.data) ? booksRes.data : []);
      setServers(Array.isArray(serversRes.data) ? serversRes.data : []);
      setCollections(Array.isArray(collectionsRes.data) ? collectionsRes.data : []);
    } catch (error) {
      console.error('Failed to fetch library:', error);
    }
  };

  // Refetch just the books quietly (no loading spinner) so progress,
  // bookmarks and chapter changes made from the player show up here without
  // needing to leave and come back to this page.
  const refreshBooksQuietly = async () => {
    try {
      const booksRes = await axios.get(`${getApiBase()}/books`);
      setBooks(Array.isArray(booksRes.data) ? booksRes.data : []);
    } catch (error) {
      console.error('Failed to refresh library:', error);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));

    const interval = setInterval(refreshBooksQuietly, 4000);
    return () => clearInterval(interval);
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
      if (isCapacitorPlatform) {
        await mobilePlayerStore.playById(bookId);
      } else {
        await axios.post(`${getApiBase()}/player/play`, { book_id: bookId });
      }
    } catch (error) {
      console.error('Failed to play book:', error);
    }
  };

  const handleDismissProgress = (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    setConfirmDismissId(bookId);
  };

  const confirmDismissProgress = async () => {
    const bookId = confirmDismissId;
    if (!bookId) return;
    setConfirmDismissId(null);
    setBooks(prev => prev.map(b => (b.id === bookId ? { ...b, progress_percent: 0, current_chapter_title: null } : b)));
    try {
      // If this book is the one currently loaded in the player, stop
      // playback too - keeping it playing after removing its progress
      // would just recreate the progress a few seconds later via autosave.
      const stateRes = await axios.get(`${getApiBase()}/player/state`);
      if (stateRes.data.currentBook?.id === bookId) {
        await axios.post(`${getApiBase()}/player/stop`);
      }
      await axios.delete(`${getApiBase()}/books/${bookId}/progress`);
    } catch (error) {
      console.error('Failed to reset book progress:', error);
      fetchAll();
    }
  };

  const handleSync = async () => {
    if (syncing) return;
    try {
      setSyncing(true);
      setSyncMessage('Synchronisation...');
      await axios.post(`${getApiBase()}/sync`);

      // The sync runs in a background thread on the backend; poll its status
      // until it's done, then refresh the library so new/updated books show up.
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${getApiBase()}/sync/status`);
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

  // "In progress" = has been started but not finished. Shown bigger, above
  // the full library grid. They also stay visible (more discreetly) in
  // "Toute la bibliothèque" below, per user preference.
  const inProgressBooks = useMemo(
    () => books.filter(b => b.progress_percent > 0 && b.progress_percent < 100),
    [books]
  );

  const sortedLibraryBooks = useMemo(() => {
    const list = [...filteredBooks];
    switch (sortMode) {
      case 'alphabetical':
        return list.sort((a, b) => a.title.localeCompare(b.title));
      case 'author':
        return list.sort((a, b) => a.author.localeCompare(b.author) || a.title.localeCompare(b.title));
      case 'progress':
        return list.sort((a, b) => b.progress_percent - a.progress_percent || a.title.localeCompare(b.title));
      case 'bookmark':
        return list.sort((a, b) => {
          if (a.has_bookmark !== b.has_bookmark) return a.has_bookmark ? -1 : 1;
          return a.title.localeCompare(b.title);
        });
      case 'genre':
        return list.sort((a, b) => {
          const keyCompare = genreGroupKey(a).localeCompare(genreGroupKey(b));
          return keyCompare || a.title.localeCompare(b.title);
        });
      case 'collection':
        // Actual grouping/ordering for this mode comes from collectionGroups
        // below (a book can belong to several collections, unlike
        // series/genre) - this is just a sane base order.
        return list.sort((a, b) => a.title.localeCompare(b.title));
      case 'series':
      default:
        return list.sort((a, b) => {
          const aKey = seriesGroupKey(a);
          const bKey = seriesGroupKey(b);
          const aNoSeries = aKey === NO_SERIES_LABEL;
          const bNoSeries = bKey === NO_SERIES_LABEL;
          // Real series first (alphabetically), the "Sans série" bucket last,
          // sorted by author then title within it.
          if (aNoSeries !== bNoSeries) return aNoSeries ? 1 : -1;
          if (aNoSeries && bNoSeries) {
            return a.author.localeCompare(b.author) || a.title.localeCompare(b.title);
          }
          const keyCompare = aKey.localeCompare(bKey);
          if (keyCompare) return keyCompare;
          // Within the same series, order by tome/sequence number (as
          // Audiobookshelf reports it) instead of alphabetically by title -
          // titles rarely sort into reading order on their own.
          const seqA = parseFloat(String(a.series_sequence));
          const seqB = parseFloat(String(b.series_sequence));
          if (!isNaN(seqA) && !isNaN(seqB) && seqA !== seqB) return seqA - seqB;
          return a.title.localeCompare(b.title);
        });
    }
  }, [filteredBooks, sortMode]);

  // When sorting "by series" or "by genre", group consecutive books under
  // their series/author (or genre) key so it reads as an actual grouped
  // catalog, not just a flat sorted list.
  const seriesGroups = useMemo(() => {
    if (sortMode !== 'series' && sortMode !== 'genre') return null;
    const keyFn = sortMode === 'genre' ? genreGroupKey : seriesGroupKey;
    const groups: { key: string; books: Book[] }[] = [];
    for (const book of sortedLibraryBooks) {
      const key = keyFn(book);
      const last = groups[groups.length - 1];
      if (last && last.key === key) {
        last.books.push(book);
      } else {
        groups.push({ key, books: [book] });
      }
    }
    return groups;
  }, [sortedLibraryBooks, sortMode]);

  // "Par collection" groups differently from series/genre: a book can
  // belong to several collections at once, so it's not a single-key
  // partition - each collection contributes its own group (in membership
  // order), and anything left over falls into a shared "Sans collection"
  // bucket.
  const collectionGroups = useMemo(() => {
    if (sortMode !== 'collection') return null;
    const byId = new Map(filteredBooks.map(b => [b.id, b]));
    const groups: { key: string; books: Book[] }[] = [];
    const seen = new Set<string>();
    collections.forEach(collection => {
      const groupBooks = collection.book_ids
        .map(id => byId.get(id))
        .filter((b): b is Book => Boolean(b));
      groupBooks.forEach(b => seen.add(b.id));
      if (groupBooks.length > 0) {
        groups.push({ key: collection.name, books: groupBooks });
      }
    });
    const remaining = filteredBooks
      .filter(b => !seen.has(b.id))
      .sort((a, b) => a.author.localeCompare(b.author) || a.title.localeCompare(b.title));
    if (remaining.length > 0) {
      groups.push({ key: NO_COLLECTION_LABEL, books: remaining });
    }
    return groups;
  }, [sortMode, collections, filteredBooks]);

  const renderBookCard = (book: Book, discreet = false) => (
    <div key={book.id} className="book-card" onClick={() => navigate(`/book/${book.id}`)}>
      <div className="book-card-cover">
        {book.cover_url ? (
          <CoverImage bookId={book.id} coverUrl={book.cover_url} alt={book.title} />
        ) : (
          <span>📚</span>
        )}
        <span className="book-card-badge">{formatDuration(book.duration)}</span>
        {book.is_finished && (
          <span className="book-card-finished" title="Livre terminé">
            <Check size={14} strokeWidth={3} />
          </span>
        )}
        {book.has_bookmark && (
          <span className="book-card-bookmark" title="Marque-page enregistré">
            <Bookmark size={12} fill="currentColor" />
          </span>
        )}
        <div className="book-card-overlay">
          <button className="play-button" onClick={(e) => handlePlayBook(e, book.id)} title="Lire">
            <Play size={18} fill="currentColor" />
          </button>
        </div>
        {book.progress_percent > 0 && (
          <>
            {!discreet && (
              <button
                className={`book-card-dismiss ${isCapacitorPlatform ? 'book-card-dismiss-mobile' : ''}`}
                onClick={(e) => handleDismissProgress(e, book.id)}
                title="Retirer de Reprendre l'écoute"
              >
                <X size={12} />
              </button>
            )}
            <div className="book-card-progress-bar">
              <div className="book-card-progress-fill" style={{ width: `${book.progress_percent}%` }} />
            </div>
          </>
        )}
      </div>
      <div className="book-card-info">
        <div className="book-card-title">{book.title}</div>
        <div className="book-card-author">{book.author}</div>
        {!discreet && book.current_chapter_title && (
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
                {inProgressBooks.map(b => renderBookCard(b, false))}
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

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '34px', marginBottom: '16px' }}>
            <h2 className="section-title" style={{ margin: 0 }}>Toute la bibliothèque</h2>
            <div style={{ position: 'relative' }}>
              <button
                className="library-sort-button"
                onClick={() => setShowSortMenu(!showSortMenu)}
              >
                {SORT_LABELS[sortMode]} <ChevronDown size={14} />
              </button>
              {showSortMenu && (
                <>
                  <div className="library-sort-backdrop" onClick={() => setShowSortMenu(false)} />
                  <div className="library-sort-menu">
                    {(Object.keys(SORT_LABELS) as SortMode[]).map(mode => (
                      <button
                        key={mode}
                        className={`library-sort-option ${sortMode === mode ? 'active' : ''}`}
                        onClick={() => {
                          setSortMode(mode);
                          setShowSortMenu(false);
                        }}
                      >
                        {SORT_LABELS[mode]}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {sortedLibraryBooks.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', padding: '20px 0' }}>
              Aucun audiolivre ne correspond.
            </div>
          ) : (sortMode === 'series' || sortMode === 'genre') && seriesGroups ? (
            seriesGroups.map(group => (
              <div key={group.key} style={{ marginBottom: '30px' }}>
                <h3 className="library-group-title">{group.key}</h3>
                <div className="books-grid">
                  {group.books.map(b => renderBookCard(b, true))}
                </div>
              </div>
            ))
          ) : sortMode === 'collection' && collectionGroups ? (
            collectionGroups.map(group => (
              <div key={group.key} style={{ marginBottom: '30px' }}>
                <h3 className="library-group-title">{group.key}</h3>
                <div className="books-grid">
                  {group.books.map(b => renderBookCard(b, true))}
                </div>
              </div>
            ))
          ) : (
            <div className="books-grid">
              {sortedLibraryBooks.map(b => renderBookCard(b, true))}
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmDismissId !== null}
        title="Retirer de Reprendre l'écoute"
        message="La progression de ce livre sera réinitialisée et sa lecture en cours sera arrêtée. Continuer ?"
        confirmLabel="Retirer"
        danger
        onConfirm={confirmDismissProgress}
        onCancel={() => setConfirmDismissId(null)}
      />
    </div>
  );
};

export default HomePage;
