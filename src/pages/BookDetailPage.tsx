import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, ArrowLeft, Search, Pencil, Lock } from 'lucide-react';
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
  manual_overrides: string[];
  progress: {
    position: number;
    percentage: number;
  };
}

interface MatchCandidate {
  work_key: string;
  title: string;
  author: string | null;
  year: number | null;
  cover_url: string | null;
  is_french: boolean;
}

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

// Lighter variant for secondary, repeated actions inside a panel (e.g. one
// per search result row), so the page isn't wall-to-wall accent yellow.
const mutedButtonStyle: React.CSSProperties = {
  ...smallButtonStyle,
  background: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  padding: '9px 16px',
  fontSize: '13px'
};

const BookDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeChapterIndex, setActiveChapterIndex] = useState<number | null>(null);
  const apiBase = 'http://localhost:5000/api';

  // "Associer" (match) panel
  const [showMatchPanel, setShowMatchPanel] = useState(false);
  const [matchQuery, setMatchQuery] = useState('');
  const [matchCandidates, setMatchCandidates] = useState<MatchCandidate[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchMode, setMatchMode] = useState<'fill' | 'replace'>('fill');
  const [applyingKey, setApplyingKey] = useState<string | null>(null);

  // Manual edit form
  const [showEditForm, setShowEditForm] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editAuthor, setEditAuthor] = useState('');
  const [editNarrator, setEditNarrator] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editCoverUrl, setEditCoverUrl] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

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

  useEffect(() => {
    if (id) {
      fetchBookDetail();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const openMatchPanel = () => {
    setShowEditForm(false);
    setShowMatchPanel(!showMatchPanel);
    if (!showMatchPanel) {
      setMatchQuery('');
      setMatchCandidates([]);
      handleSearchCandidates('');
    }
  };

  const handleSearchCandidates = async (query: string) => {
    if (!book) return;
    try {
      setMatchLoading(true);
      const response = await axios.get(`${apiBase}/books/${book.id}/match-candidates`, {
        params: query ? { query } : {}
      });
      setMatchCandidates(response.data);
    } catch (error) {
      console.error('Failed to search candidates:', error);
    } finally {
      setMatchLoading(false);
    }
  };

  const handleApplyMatch = async (workKey: string) => {
    if (!book) return;
    try {
      setApplyingKey(workKey);
      await axios.post(`${apiBase}/books/${book.id}/match`, { work_key: workKey, mode: matchMode });
      setShowMatchPanel(false);
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to apply match:', error);
    } finally {
      setApplyingKey(null);
    }
  };

  const openEditForm = () => {
    if (!book) return;
    setShowMatchPanel(false);
    setEditTitle(book.title);
    setEditAuthor(book.author);
    setEditNarrator(book.narrator || '');
    setEditDescription(book.description || '');
    setEditCoverUrl(book.cover_url || '');
    setShowEditForm(!showEditForm);
  };

  const handleSaveEdit = async () => {
    if (!book) return;
    try {
      setSavingEdit(true);
      await axios.patch(`${apiBase}/books/${book.id}`, {
        title: editTitle.trim(),
        author: editAuthor.trim(),
        narrator: editNarrator.trim() || null,
        description: editDescription.trim() || null,
        cover_url: editCoverUrl.trim() || null
      });
      setShowEditForm(false);
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to save edit:', error);
    } finally {
      setSavingEdit(false);
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

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
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
            <button className="cta-button" style={smallButtonStyle} onClick={openMatchPanel}>
              <Search size={14} /> Associer
            </button>
            <button className="cta-button" style={smallButtonStyle} onClick={openEditForm}>
              <Pencil size={14} /> Modifier
            </button>
          </div>

          {showMatchPanel && (
            <div
              style={{
                marginTop: '20px',
                backgroundColor: 'var(--surface)',
                boxShadow: 'var(--shadow-pop)',
                borderRadius: 'var(--radius-md)',
                padding: '20px',
                maxWidth: '520px'
              }}
            >
              <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
                <input
                  type="text"
                  value={matchQuery}
                  onChange={(e) => setMatchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchCandidates(matchQuery)}
                  placeholder={`${book.title} ${book.author}`}
                  style={{ ...inputStyle, flex: 1 }}
                />
                <button
                  className="cta-button"
                  style={mutedButtonStyle}
                  onClick={() => handleSearchCandidates(matchQuery)}
                >
                  Chercher
                </button>
              </div>

              <div style={{ display: 'flex', gap: '14px', marginBottom: '14px', fontSize: '13px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="radio" checked={matchMode === 'fill'} onChange={() => setMatchMode('fill')} />
                  Compléter (garde ce qui existe)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="radio" checked={matchMode === 'replace'} onChange={() => setMatchMode('replace')} />
                  Remplacer
                </label>
              </div>

              {matchLoading ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Recherche...</p>
              ) : matchCandidates.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Aucun résultat</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '360px', overflowY: 'auto' }}>
                  {matchCandidates.map((c) => (
                    <div
                      key={c.work_key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '8px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--surface-muted)'
                      }}
                    >
                      <div style={{ width: '40px', height: '56px', flexShrink: 0, borderRadius: '6px', overflow: 'hidden', backgroundColor: 'var(--background)' }}>
                        {c.cover_url && <img src={c.cover_url} alt={c.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {c.title}
                          {c.is_french && (
                            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--accent-ink)', background: 'var(--accent)', padding: '2px 6px', borderRadius: '999px' }}>
                              FR
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {c.author} {c.year ? `· ${c.year}` : ''}
                        </div>
                      </div>
                      <button
                        className="cta-button"
                        style={{ ...mutedButtonStyle, opacity: applyingKey === c.work_key ? 0.6 : 1 }}
                        disabled={applyingKey === c.work_key}
                        onClick={() => handleApplyMatch(c.work_key)}
                      >
                        {applyingKey === c.work_key ? '...' : 'Choisir'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {showEditForm && (
            <div
              style={{
                marginTop: '20px',
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
              <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Titre" style={inputStyle} />
              <input type="text" value={editAuthor} onChange={(e) => setEditAuthor(e.target.value)} placeholder="Auteur" style={inputStyle} />
              <input type="text" value={editNarrator} onChange={(e) => setEditNarrator(e.target.value)} placeholder="Narrateur" style={inputStyle} />
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Description"
                rows={4}
                style={{ ...inputStyle, borderRadius: 'var(--radius-sm)', resize: 'vertical', fontFamily: 'inherit' }}
              />
              <input type="text" value={editCoverUrl} onChange={(e) => setEditCoverUrl(e.target.value)} placeholder="URL de couverture" style={inputStyle} />
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

          {book.manual_overrides && book.manual_overrides.length > 0 && (
            <p style={{ marginTop: '14px', fontSize: '11px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={11} /> Modifié manuellement, protégé des prochaines synchronisations
            </p>
          )}
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
