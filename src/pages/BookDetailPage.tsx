import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, ArrowLeft } from 'lucide-react';
import axios from 'axios';

interface BookDetail {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
  duration: number;
  description: string;
  chapters: Array<{
    id: string;
    title: string;
    index: number;
    duration: number;
  }>;
  progress: {
    position: number;
    percentage: number;
  };
}

const BookDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeChapterIndex, setActiveChapterIndex] = useState<number | null>(null);
  const apiBase = 'http://localhost:5000/api';

  useEffect(() => {
    const fetchBookDetail = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${apiBase}/books/${id}`);
        setBook(response.data);
      } catch (error) {
        console.error('Failed to fetch book details:', error);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchBookDetail();
    }
  }, [id]);

  useEffect(() => {
    const fetchPlayerState = async () => {
      try {
        const response = await axios.get(`${apiBase}/player/state`);
        if (response.data.currentBook?.id === id) {
          setActiveChapterIndex(response.data.currentChapterIndex ?? null);
        } else {
          setActiveChapterIndex(null);
        }
      } catch (error) {
        console.error('Failed to get player state:', error);
      }
    };

    fetchPlayerState();
    const interval = setInterval(fetchPlayerState, 2000);
    return () => clearInterval(interval);
  }, [id]);

  const handlePlayBook = async () => {
    if (book) {
      try {
        await axios.post(`${apiBase}/player/play`, { book_id: book.id });
      } catch (error) {
        console.error('Failed to play book:', error);
      }
    }
  };

  const handlePlayChapter = async (chapterIndex: number) => {
    if (book) {
      try {
        await axios.post(`${apiBase}/player/play`, { book_id: book.id, chapter_index: chapterIndex });
      } catch (error) {
        console.error('Failed to play chapter:', error);
      }
    }
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}min`;
  };

  if (loading) {
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
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement...
        </div>
      </div>
    );
  }

  if (!book) {
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
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Audiolive non trouvé
        </div>
      </div>
    );
  }

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

      <div style={{ display: 'flex', gap: '30px', marginBottom: '30px' }}>
        <div
          style={{
            width: '200px',
            height: '300px',
            borderRadius: '8px',
            overflow: 'hidden',
            flexShrink: 0,
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)'
          }}
        >
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={book.title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: '48px' }}>
              📚
            </div>
          )}
        </div>

        <div style={{ flex: 1 }}>
          <h1 className="page-title" style={{ marginBottom: '10px' }}>
            {book.title}
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
            par {book.author}
          </p>
          {book.narrator && (
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Narrateur : {book.narrator}
            </p>
          )}

          <div style={{ marginBottom: '20px' }}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>Durée</p>
            <p style={{ fontSize: '16px' }}>{formatTime(book.duration)}</p>
          </div>

          {book.progress.percentage > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>Progression</p>
              <div
                style={{
                  width: '100%',
                  height: '8px',
                  backgroundColor: 'var(--border)',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}
              >
                <div
                  style={{
                    width: `${book.progress.percentage}%`,
                    height: '100%',
                    backgroundColor: 'var(--primary)'
                  }}
                />
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '8px' }}>
                {book.progress.percentage.toFixed(1)}% complété
              </p>
            </div>
          )}

          <button
            className="cta-button"
            onClick={handlePlayBook}
            style={{
              background: 'var(--primary)',
              color: 'var(--secondary)',
              border: 'none',
              padding: '12px 30px',
              borderRadius: '999px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <Play size={20} /> Lire
          </button>
        </div>
      </div>

      {book.description && (
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ color: 'var(--primary)', marginBottom: '10px' }}>Description</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            {book.description}
          </p>
        </div>
      )}

      {book.chapters && book.chapters.length > 0 && (
        <div>
          <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>Chapitres</h2>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '0 15px 8px',
              color: 'var(--text-secondary)',
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}
          >
            <span>Titre</span>
            <span>Durée</span>
          </div>
          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              overflow: 'hidden'
            }}
          >
            {book.chapters.map((chapter, index) => {
              const isActive = activeChapterIndex === index;
              return (
                <div
                  key={chapter.id}
                  onClick={() => handlePlayChapter(index)}
                  style={{
                    padding: '12px 15px',
                    borderBottom: index < book.chapters.length - 1 ? '1px solid var(--border)' : 'none',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    gap: '10px',
                    backgroundColor: isActive ? 'var(--surface-muted)' : 'transparent'
                  }}
                >
                  <span
                    style={{
                      color: isActive ? 'var(--primary)' : 'var(--text-primary)',
                      fontWeight: isActive ? 700 : 400,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      minWidth: 0
                    }}
                  >
                    <Play size={14} style={{ flexShrink: 0, color: isActive ? 'var(--primary)' : 'var(--text-secondary)' }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {index + 1}. {chapter.title}
                    </span>
                  </span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '12px', flexShrink: 0 }}>
                    {Math.floor(chapter.duration / 60)}m
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default BookDetailPage;
