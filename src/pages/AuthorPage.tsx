import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, User } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

interface Book {
  id: string;
  title: string;
  author: string;
  cover_url: string | null;
  duration: number;
  author_bio: string | null;
  author_photo: string | null;
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '--';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}` : `${minutes}min`;
};

const AuthorPage: React.FC = () => {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const authorName = name ? decodeURIComponent(name) : '';

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE}/books`);
        setBooks(response.data.filter((b: Book) => b.author === authorName));
      } catch (error) {
        console.error('Failed to fetch author books:', error);
      } finally {
        setLoading(false);
      }
    };

    if (authorName) {
      fetchBooks();
    }
  }, [authorName]);

  const { bio, photo } = useMemo(() => {
    const withBio = books.find(b => b.author_bio);
    const withPhoto = books.find(b => b.author_photo);
    return { bio: withBio?.author_bio || null, photo: withPhoto?.author_photo || null };
  }, [books]);

  const handlePlayBook = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    try {
      await axios.post(`${API_BASE}/player/play`, { book_id: bookId });
    } catch (error) {
      console.error('Failed to play book:', error);
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

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px' }}>
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
        <div style={{ minWidth: 0 }}>
          <h1 className="page-title" style={{ marginBottom: bio ? '8px' : 0 }}>{authorName}</h1>
          {bio && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.6, maxWidth: '640px' }}>
              {bio}
            </p>
          )}
        </div>
      </div>

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
