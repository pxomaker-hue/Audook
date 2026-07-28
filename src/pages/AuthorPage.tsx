import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, User, Pencil, RefreshCw, Bookmark, CheckCircle2 } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../config';
import { isCapacitorPlatform } from '../native/platform';
import { mobilePlayerStore } from '../native/mobilePlayerStore';

interface Book {
  id: string;
  title: string;
  author: string;
  cover_url: string | null;
  duration: number;
  has_bookmark: boolean;
  is_finished: boolean;
  author_bio: string | null;
  author_photo: string | null;
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '--';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}` : `${minutes}min`;
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 14px',
  backgroundColor: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  borderRadius: '999px',
  fontFamily: 'inherit',
  fontSize: '13px'
};

const smallButtonStyle: React.CSSProperties = {
  background: 'var(--primary)',
  color: 'var(--secondary)',
  border: 'none',
  padding: '12px 24px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 600,
  display: 'flex',
  alignItems: 'center',
  gap: '8px'
};

const AuthorPage: React.FC = () => {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const authorName = name ? decodeURIComponent(name) : '';

  const [showEditForm, setShowEditForm] = useState(false);
  const [editBio, setEditBio] = useState('');
  const [editPhoto, setEditPhoto] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${getApiBase()}/books`);
      setBooks(response.data.filter((b: Book) => b.author === authorName));
    } catch (error) {
      console.error('Failed to fetch author books:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authorName) {
      fetchBooks();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorName]);

  const { bio, photo } = useMemo(() => {
    const withBio = books.find(b => b.author_bio);
    const withPhoto = books.find(b => b.author_photo);
    return { bio: withBio?.author_bio || null, photo: withPhoto?.author_photo || null };
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

  const openEditForm = () => {
    setEditBio(bio || '');
    setEditPhoto(photo || '');
    setShowEditForm(!showEditForm);
  };

  const handleSaveEdit = async () => {
    try {
      setSavingEdit(true);
      await axios.patch(`${getApiBase()}/authors/${encodeURIComponent(authorName)}`, {
        bio: editBio.trim() || null,
        photo: editPhoto.trim() || null
      });
      setShowEditForm(false);
      await fetchBooks();
    } catch (error) {
      console.error('Failed to save author edit:', error);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleRefreshOnline = async () => {
    try {
      setRefreshing(true);
      setRefreshMessage(null);
      const response = await axios.post(`${getApiBase()}/authors/${encodeURIComponent(authorName)}/refresh`);
      if (response.data.status === 'not_found') {
        setRefreshMessage("Rien trouvé en ligne pour cet auteur");
      } else {
        await fetchBooks();
        setRefreshMessage('Mis à jour depuis Wikipédia');
      }
    } catch (error) {
      console.error('Failed to refresh author:', error);
      setRefreshMessage('Échec de la récupération');
    } finally {
      setRefreshing(false);
      setTimeout(() => setRefreshMessage(null), 4000);
    }
  };

  return (
    <div className="page-content">
      <button
        onClick={() => navigate(-1)}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--primary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '20px',
          fontSize: '14px'
        }}
      >
        <ArrowLeft size={20} /> Retour
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '16px' }}>
        <div
          style={{
            width: '84px',
            height: '84px',
            borderRadius: '50%',
            overflow: 'hidden',
            flexShrink: 0,
            backgroundColor: 'var(--surface-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-pop)'
          }}
        >
          {photo ? (
            <img src={photo} alt={authorName} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <User size={36} color="var(--text-tertiary)" />
          )}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h1 className="page-title" style={{ marginBottom: bio ? '8px' : 0 }}>{authorName}</h1>
          {bio && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.6, maxWidth: '640px' }}>
              {bio}
            </p>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button className="cta-button" style={smallButtonStyle} onClick={openEditForm}>
          <Pencil size={14} /> Modifier
        </button>
        <button
          className="cta-button"
          style={{ ...smallButtonStyle, opacity: refreshing ? 0.7 : 1 }}
          onClick={handleRefreshOnline}
          disabled={refreshing}
        >
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} /> Rafraîchir depuis le web
        </button>
        {refreshMessage && (
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{refreshMessage}</span>
        )}
      </div>

      {showEditForm && (
        <div
          style={{
            marginBottom: '30px',
            backgroundColor: 'var(--surface)',
            boxShadow: 'var(--shadow-pop)',
            borderRadius: 'var(--radius-md)',
            padding: '20px',
            maxWidth: '520px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}
        >
          <textarea
            value={editBio}
            onChange={(e) => setEditBio(e.target.value)}
            placeholder="Biographie"
            rows={5}
            style={{ ...inputStyle, borderRadius: 'var(--radius-sm)', resize: 'vertical', fontFamily: 'inherit' }}
          />
          <input
            type="text"
            value={editPhoto}
            onChange={(e) => setEditPhoto(e.target.value)}
            placeholder="URL de la photo"
            style={inputStyle}
          />
          <div>
            <button
              className="cta-button"
              style={{ ...smallButtonStyle, background: 'var(--primary)', color: 'var(--secondary)', opacity: savingEdit ? 0.6 : 1 }}
              disabled={savingEdit}
              onClick={handleSaveEdit}
            >
              {savingEdit ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement...
        </div>
      ) : books.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucun livre trouvé pour cet auteur.
        </div>
      ) : (
        <div className="books-grid">
          {books.map(book => (
            <div key={book.id} className="book-card" onClick={() => navigate(`/book/${book.id}`)}>
              <div className="book-card-cover">
                {book.cover_url ? (
                  <img src={book.cover_url} alt={book.title} />
                ) : (
                  <span>📚</span>
                )}
                <span className="book-card-badge">{formatDuration(book.duration)}</span>
                {book.is_finished && (
                  <span className="book-card-finished" title="Livre terminé">
                    <CheckCircle2 size={12} fill="currentColor" />
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
              </div>
              <div className="book-card-info">
                <div className="book-card-title">{book.title}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AuthorPage;
