import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, ArrowLeft, Search, Pencil, Lock, Unlock, Bookmark, Trash2, Loader2, CheckCircle2, Sparkles } from 'lucide-react';
import axios from 'axios';

interface BookmarkEntry {
  id: number;
  chapter_index: number;
  position_seconds: number;
  title: string | null;
  created_at: string | null;
}

interface BookDetail {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
  duration: number;
  description: string;
  series: string | null;
  series_sequence: string | number | null;
  genre: string[];
  chapters: Array<{
    id: string;
    title: string;
    index: number;
    duration: number;
  }>;
  bookmarks: BookmarkEntry[];
  manual_overrides: string[];
  progress: {
    position: number;
    percentage: number;
    chapter_index: number;
  };
  is_finished: boolean;
  noise_reduction_status: 'idle' | 'processing' | 'done' | 'error';
  use_cleaned_audio: boolean;
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
  const [activePosition, setActivePosition] = useState<number>(0);
  const apiBase = 'http://localhost:5000/api';

  // "Associer" (match) panel
  const [showMatchPanel, setShowMatchPanel] = useState(false);
  const [matchQuery, setMatchQuery] = useState('');
  const [matchCandidates, setMatchCandidates] = useState<MatchCandidate[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchMode, setMatchMode] = useState<'fill' | 'replace'>('fill');
  const [applyingKey, setApplyingKey] = useState<string | null>(null);
  const [showAllCandidates, setShowAllCandidates] = useState(false);

  // Manual edit form
  const [showEditForm, setShowEditForm] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editAuthor, setEditAuthor] = useState('');
  const [editNarrator, setEditNarrator] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editCoverUrl, setEditCoverUrl] = useState('');
  const [editSeries, setEditSeries] = useState('');
  const [editGenre, setEditGenre] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [unlockingField, setUnlockingField] = useState<string | null>(null);
  const [resumingBookmarkId, setResumingBookmarkId] = useState<number | null>(null);
  const [togglingFinished, setTogglingFinished] = useState(false);
  const [startingCleanAudio, setStartingCleanAudio] = useState(false);
  const [togglingCleanedAudio, setTogglingCleanedAudio] = useState(false);

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

  const fetchPlayerState = async () => {
    try {
      const response = await axios.get(`${apiBase}/player/state`);
      if (response.data.currentBook?.id === id) {
        setActiveChapterIndex(response.data.currentChapterIndex ?? null);
        setActivePosition(response.data.position ?? 0);
      } else {
        setActiveChapterIndex(null);
      }
    } catch (error) {
      console.error('Failed to get player state:', error);
    }
  };

  useEffect(() => {
    fetchPlayerState();
    const interval = setInterval(fetchPlayerState, 2000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // While a noise-reduction pass is running in the background, poll for it
  // to finish so the button/status updates without a manual refresh.
  useEffect(() => {
    if (book?.noise_reduction_status !== 'processing') return;
    const interval = setInterval(fetchBookDetail, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book?.noise_reduction_status]);

  const handlePlayBook = async () => {
    if (book) {
      try {
        await axios.post(`${apiBase}/player/play`, { book_id: book.id });
        // Don't wait for the next 2s poll to highlight the chapter that
        // just started - refresh right away so it's instant.
        fetchPlayerState();
      } catch (error) {
        console.error('Failed to play book:', error);
      }
    }
  };

  const handlePlayChapter = async (chapterIndex: number) => {
    if (book) {
      try {
        await axios.post(`${apiBase}/player/play`, { book_id: book.id, chapter_index: chapterIndex });
        fetchPlayerState();
      } catch (error) {
        console.error('Failed to play chapter:', error);
      }
    }
  };

  const handleToggleFinished = async () => {
    if (!book) return;
    try {
      setTogglingFinished(true);
      await axios.post(`${apiBase}/books/${book.id}/finished`, { finished: !book.is_finished });
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to toggle finished status:', error);
    } finally {
      setTogglingFinished(false);
    }
  };

  const handleCleanAudio = async () => {
    if (!book) return;
    try {
      setStartingCleanAudio(true);
      await axios.post(`${apiBase}/books/${book.id}/clean-audio`);
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to start noise reduction:', error);
    } finally {
      setStartingCleanAudio(false);
    }
  };

  const handleToggleUseCleanedAudio = async () => {
    if (!book) return;
    try {
      setTogglingCleanedAudio(true);
      await axios.post(`${apiBase}/books/${book.id}/use-cleaned-audio`, { enabled: !book.use_cleaned_audio });
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to toggle cleaned audio:', error);
    } finally {
      setTogglingCleanedAudio(false);
    }
  };

  const handleResumeBookmark = async (bookmarkId: number) => {
    try {
      setResumingBookmarkId(bookmarkId);
      await axios.post(`${apiBase}/bookmarks/${bookmarkId}/resume`);
    } catch (error) {
      console.error('Failed to resume bookmark:', error);
    } finally {
      setResumingBookmarkId(null);
    }
  };

  const handleDeleteBookmark = async (bookmarkId: number) => {
    try {
      await axios.delete(`${apiBase}/bookmarks/${bookmarkId}`);
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to delete bookmark:', error);
    }
  };

  const openMatchPanel = () => {
    setShowEditForm(false);
    setShowMatchPanel(!showMatchPanel);
    if (!showMatchPanel) {
      setMatchQuery('');
      setMatchCandidates([]);
      setShowAllCandidates(false);
      handleSearchCandidates('');
    }
  };

  const handleSearchCandidates = async (query: string) => {
    if (!book) return;
    try {
      setMatchLoading(true);
      setShowAllCandidates(false);
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

  const handleApplyMatch = async (candidate: MatchCandidate) => {
    if (!book) return;
    try {
      setApplyingKey(candidate.work_key);
      // The candidate's title/author come straight from the search result -
      // get_book_work_details only fetches description/cover/genre, so
      // without sending these along, picking a match never actually
      // corrected the title/author shown in the search list.
      await axios.post(`${apiBase}/books/${book.id}/match`, {
        work_key: candidate.work_key,
        mode: matchMode,
        title: candidate.title,
        author: candidate.author
      });
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
    setEditSeries(book.series || '');
    setEditGenre((book.genre || []).join(', '));
    setShowEditForm(!showEditForm);
  };

  const handleSaveEdit = async () => {
    if (!book) return;
    try {
      setSavingEdit(true);
      // Only send fields the user actually changed - the backend locks
      // every field it receives, so resending the whole form unconditionally
      // would silently re-lock a field the user had just unlocked (even
      // without touching it) the moment "Enregistrer" is clicked.
      const payload: Record<string, any> = {};
      const nextTitle = editTitle.trim();
      const nextAuthor = editAuthor.trim();
      const nextNarrator = editNarrator.trim() || null;
      const nextDescription = editDescription.trim() || null;
      const nextCoverUrl = editCoverUrl.trim() || null;
      const nextSeries = editSeries.trim() || null;
      const nextGenre = editGenre.split(',').map(g => g.trim()).filter(Boolean);

      if (nextTitle !== book.title) payload.title = nextTitle;
      if (nextAuthor !== book.author) payload.author = nextAuthor;
      if (nextNarrator !== (book.narrator || null)) payload.narrator = nextNarrator;
      if (nextDescription !== (book.description || null)) payload.description = nextDescription;
      if (nextCoverUrl !== (book.cover_url || null)) payload.cover_url = nextCoverUrl;
      if (nextSeries !== (book.series || null)) payload.series = nextSeries;
      if (JSON.stringify(nextGenre) !== JSON.stringify(book.genre || [])) payload.genre = nextGenre;

      if (Object.keys(payload).length > 0) {
        await axios.patch(`${apiBase}/books/${book.id}`, payload);
      }
      setShowEditForm(false);
      await fetchBookDetail();
    } catch (error) {
      console.error('Failed to save edit:', error);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleToggleFieldLock = async (field: string, currentlyLocked: boolean) => {
    if (!book) return;
    try {
      setUnlockingField(field);
      const action = currentlyLocked ? 'unlock' : 'lock';
      await axios.post(`${apiBase}/books/${book.id}/${action}`, { fields: [field] });
      await fetchBookDetail();
    } catch (error) {
      console.error(`Failed to ${currentlyLocked ? 'unlock' : 'lock'} field:`, error);
    } finally {
      setUnlockingField(null);
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
          <p style={{ color: 'var(--text-secondary)', marginBottom: book.series ? '4px' : '20px' }}>
            par {book.author}
          </p>
          {book.series && (
            <p style={{ color: 'var(--primary)', fontSize: '13px', fontWeight: 600, marginBottom: '20px' }}>
              Série : {book.series}
              {book.series_sequence != null && book.series_sequence !== '' && ` (Tome ${book.series_sequence})`}
            </p>
          )}
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
            <div className="icon-expand-wrapper" onClick={handlePlayBook} role="button" tabIndex={0}>
              <button className="icon-expand-button primary" title="Lire" tabIndex={-1}>
                <Play size={18} />
              </button>
              <span className="icon-expand-label">Lire</span>
            </div>
            <div className="icon-expand-wrapper" onClick={openMatchPanel} role="button" tabIndex={0}>
              <button className="icon-expand-button" title="Associer" tabIndex={-1}>
                <Search size={16} />
              </button>
              <span className="icon-expand-label">Associer</span>
            </div>
            <div className="icon-expand-wrapper" onClick={openEditForm} role="button" tabIndex={0}>
              <button className="icon-expand-button" title="Modifier" tabIndex={-1}>
                <Pencil size={16} />
              </button>
              <span className="icon-expand-label">Modifier</span>
            </div>
            <div
              className="icon-expand-wrapper"
              onClick={() => !togglingFinished && handleToggleFinished()}
              role="button"
              tabIndex={0}
            >
              <button
                className={`icon-expand-button ${book.is_finished ? 'confirmed' : ''}`}
                disabled={togglingFinished}
                title={book.is_finished ? 'Lu' : 'Marquer comme lu'}
                tabIndex={-1}
              >
                {togglingFinished ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
              </button>
              <span className="icon-expand-label">{book.is_finished ? 'Lu' : 'Marquer comme lu'}</span>
            </div>
            <div
              className="icon-expand-wrapper"
              onClick={() => {
                if (startingCleanAudio || togglingCleanedAudio || book.noise_reduction_status === 'processing') return;
                // Once cleaned, clicking flips between the cleaned and
                // original audio instead of re-running the pass - the
                // cleaned files stay cached, so this is instant either way.
                if (book.noise_reduction_status === 'done') {
                  handleToggleUseCleanedAudio();
                } else {
                  handleCleanAudio();
                }
              }}
              role="button"
              tabIndex={0}
            >
              <button
                className={`icon-expand-button ${book.noise_reduction_status === 'done' && book.use_cleaned_audio ? 'confirmed' : ''}`}
                disabled={startingCleanAudio || togglingCleanedAudio || book.noise_reduction_status === 'processing'}
                title={
                  book.noise_reduction_status === 'done'
                    ? (book.use_cleaned_audio ? 'Audio nettoyé actif - cliquer pour revenir à l\'original' : 'Audio original actif - cliquer pour reprendre la version nettoyée')
                    : book.noise_reduction_status === 'processing' ? 'Nettoyage en cours...'
                    : book.noise_reduction_status === 'error' ? 'Échec (ffmpeg manquant ?) - Réessayer'
                    : 'Nettoyer le souffle/bruit de fond (traitement en arrière-plan)'
                }
                tabIndex={-1}
              >
                {startingCleanAudio || togglingCleanedAudio || book.noise_reduction_status === 'processing' ? (
                  <Loader2 size={16} className="spin" />
                ) : book.noise_reduction_status === 'done' && book.use_cleaned_audio ? (
                  <CheckCircle2 size={16} />
                ) : (
                  <Sparkles size={16} />
                )}
              </button>
              <span className="icon-expand-label">
                {book.noise_reduction_status === 'done'
                  ? (book.use_cleaned_audio ? 'Audio nettoyé' : 'Original (revenir au nettoyé)')
                  : book.noise_reduction_status === 'processing' ? 'Nettoyage en cours...'
                  : book.noise_reduction_status === 'error' ? 'Échec - Réessayer'
                  : 'Nettoyer le souffle'}
              </span>
            </div>
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
                  {(() => {
                    const hasAudible = matchCandidates.some(c => c.work_key.startsWith('audible:'));
                    const visible = (!showAllCandidates && hasAudible)
                      ? matchCandidates.filter(c => c.work_key.startsWith('audible:'))
                      : matchCandidates;
                    return visible;
                  })().map((c) => (
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
                          {c.work_key.startsWith('audible:') && (
                            <span
                              style={{ fontSize: '10px', fontWeight: 700, color: 'var(--secondary)', background: 'var(--primary)', padding: '2px 6px', borderRadius: '999px' }}
                              title="Résultat Audible - inclut narrateur/série/genre réels"
                            >
                              Audible
                            </span>
                          )}
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
                        onClick={() => handleApplyMatch(c)}
                      >
                        {applyingKey === c.work_key ? <Loader2 size={14} className="spin" /> : 'Choisir'}
                      </button>
                    </div>
                  ))}
                  {!showAllCandidates && matchCandidates.some(c => c.work_key.startsWith('audible:'))
                    && matchCandidates.some(c => !c.work_key.startsWith('audible:')) && (
                    <button
                      onClick={() => setShowAllCandidates(true)}
                      style={{
                        alignSelf: 'flex-start',
                        background: 'none',
                        border: 'none',
                        color: 'var(--primary)',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 600,
                        padding: '4px 0'
                      }}
                    >
                      Voir plus (Open Library, Google Books)
                    </button>
                  )}
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
              {([
                ['title', <input key="title" type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Titre" style={inputStyle} />],
                ['author', <input key="author" type="text" value={editAuthor} onChange={(e) => setEditAuthor(e.target.value)} placeholder="Auteur" style={inputStyle} />],
                ['series', <input key="series" type="text" value={editSeries} onChange={(e) => setEditSeries(e.target.value)} placeholder="Série" style={inputStyle} />],
                ['genre', <input key="genre" type="text" value={editGenre} onChange={(e) => setEditGenre(e.target.value)} placeholder="Genre(s), séparés par des virgules" style={inputStyle} />],
                ['narrator', <input key="narrator" type="text" value={editNarrator} onChange={(e) => setEditNarrator(e.target.value)} placeholder="Narrateur" style={inputStyle} />],
                ['description', (
                  <textarea
                    key="description"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    placeholder="Description"
                    rows={4}
                    style={{ ...inputStyle, borderRadius: 'var(--radius-sm)', resize: 'vertical', fontFamily: 'inherit' }}
                  />
                )],
                ['cover_url', <input key="cover_url" type="text" value={editCoverUrl} onChange={(e) => setEditCoverUrl(e.target.value)} placeholder="URL de couverture" style={inputStyle} />]
              ] as const).map(([field, input]) => {
                const isLocked = Boolean(book.manual_overrides?.includes(field));
                const isBusy = unlockingField === field;
                return (
                  <div key={field} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                    <div style={{ flex: 1 }}>{input}</div>
                    <button
                      type="button"
                      onClick={() => handleToggleFieldLock(field, isLocked)}
                      disabled={isBusy}
                      title={
                        isLocked
                          ? 'Champ verrouillé - cliquer pour déverrouiller (autorise une future synchronisation ou un remplacement à le modifier)'
                          : 'Champ déverrouillé - cliquer pour verrouiller (protège sa valeur actuelle des prochaines synchronisations/remplacements)'
                      }
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: isBusy ? 'default' : 'pointer',
                        color: isLocked ? 'var(--primary)' : 'var(--text-tertiary)',
                        display: 'flex',
                        alignItems: 'center',
                        padding: '10px 4px',
                        opacity: isBusy ? 0.5 : 1
                      }}
                    >
                      {isBusy ? <Loader2 size={14} className="spin" /> : isLocked ? <Lock size={14} /> : <Unlock size={14} />}
                    </button>
                  </div>
                );
              })}
              <div>
                <button
                  className="cta-button"
                  style={{ ...smallButtonStyle, background: 'var(--primary)', color: 'var(--secondary)', opacity: savingEdit ? 0.6 : 1 }}
                  disabled={savingEdit}
                  onClick={handleSaveEdit}
                >
                  {savingEdit ? <Loader2 size={14} className="spin" /> : 'Enregistrer'}
                </button>
              </div>
            </div>
          )}

          {book.manual_overrides && book.manual_overrides.length > 0 && (
            <p style={{ marginTop: '14px', fontSize: '11px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={11} /> Modifié manuellement, protégé des prochaines synchronisations (ouvrir "Modifier" pour déverrouiller un champ)
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

      <div style={{ marginBottom: '30px' }}>
        <h2 style={{ color: 'var(--primary)', margin: '0 0 15px' }}>Marque-pages</h2>

        {(book.bookmarks || []).length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Aucun marque-page pour ce livre.</p>
        ) : (
          <div
            style={{
              backgroundColor: 'var(--surface)',
              boxShadow: 'var(--shadow-pop)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden'
            }}
          >
            {(book.bookmarks || []).map((bookmark, index) => {
              const chapter = (book.chapters || [])[bookmark.chapter_index];
              const minutes = Math.floor(bookmark.position_seconds / 60);
              const seconds = Math.floor(bookmark.position_seconds % 60);
              return (
                <div
                  key={bookmark.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    borderBottom: index < (book.bookmarks || []).length - 1 ? '1px solid var(--border)' : 'none'
                  }}
                >
                  <Bookmark size={16} color="var(--primary)" fill="var(--primary)" style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {bookmark.title || chapter?.title || `Chapitre ${bookmark.chapter_index + 1}`}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {minutes}:{seconds.toString().padStart(2, '0')}
                    </div>
                  </div>
                  <button
                    className="cta-button"
                    style={{
                      ...mutedButtonStyle,
                      background: 'var(--primary)',
                      color: 'var(--secondary)',
                      opacity: resumingBookmarkId === bookmark.id ? 0.6 : 1
                    }}
                    disabled={resumingBookmarkId === bookmark.id}
                    onClick={() => handleResumeBookmark(bookmark.id)}
                  >
                    {resumingBookmarkId === bookmark.id ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      'Reprendre'
                    )}
                  </button>
                  <button
                    onClick={() => handleDeleteBookmark(bookmark.id)}
                    title="Supprimer ce marque-page"
                    style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', display: 'flex', padding: '6px', flexShrink: 0 }}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

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
            {(() => {
              // While actively playing this book, use the live polled
              // position; otherwise fall back to the last saved progress -
              // either way, chapters before that point read as fully
              // listened, the current one shows its own fraction, and
              // later ones are untouched.
              const referenceChapterIndex = activeChapterIndex ?? book.progress.chapter_index;
              const referencePosition = activeChapterIndex !== null ? activePosition : book.progress.position;
              return book.chapters.map((chapter, index) => {
              const isActive = activeChapterIndex === index;
              const chapterProgress = index < referenceChapterIndex
                ? 100
                : index === referenceChapterIndex && chapter.duration > 0
                ? Math.min(100, (referencePosition / chapter.duration) * 100)
                : 0;
              return (
                <div
                  key={chapter.id}
                  onClick={() => handlePlayChapter(index)}
                  style={{
                    position: 'relative',
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
                  {chapterProgress > 0 && (
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        bottom: 0,
                        height: '2px',
                        width: `${chapterProgress}%`,
                        backgroundColor: 'var(--primary)'
                      }}
                    />
                  )}
                  <span
                    style={{
                      color: isActive ? 'var(--primary)' : 'var(--text-primary)',
                      fontWeight: isActive ? 700 : 400,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '16px',
                      minWidth: 0
                    }}
                  >
                    <span
                      style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        backgroundColor: isActive ? 'var(--accent-ink)' : 'var(--surface-muted)',
                        color: isActive ? 'var(--accent)' : 'var(--text-secondary)'
                      }}
                    >
                      <Play size={13} fill="currentColor" />
                    </span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {index + 1}. {chapter.title}
                    </span>
                  </span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '12px', flexShrink: 0 }}>
                    {Math.floor(chapter.duration / 60)}m
                  </span>
                </div>
              );
              });
            })()}
          </div>
        </div>
      )}
    </div>
  );
};

export default BookDetailPage;
