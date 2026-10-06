import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, ArrowLeft, Search, Pencil, Lock, Loader2, CheckCircle2, Sparkles } from 'lucide-react';
import CoverImage from '../components/CoverImage';
import { useBookDetail } from './bookDetail/useBookDetail';
import ExpandAction from './bookDetail/ExpandAction';
import MatchPanel from './bookDetail/MatchPanel';
import EditForm from './bookDetail/EditForm';
import BookmarkList from './bookDetail/BookmarkList';
import ChapterList from './bookDetail/ChapterList';
import { BookDetail } from './bookDetail/types';
import './BookDetailPage.css';

const formatDuration = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}min`;
};

// One place for the four noise-reduction states (idle/processing/done/error)
// so the button's icon, tooltip and label can't drift apart.
const describeCleanAudio = (book: BookDetail) => {
  switch (book.noise_reduction_status) {
    case 'done':
      return book.use_cleaned_audio
        ? {
            label: 'Audio nettoyé',
            title: "Audio nettoyé actif - cliquer pour revenir à l'original"
          }
        : {
            label: 'Original (revenir au nettoyé)',
            title: 'Audio original actif - cliquer pour reprendre la version nettoyée'
          };
    case 'processing':
      return { label: 'Nettoyage en cours...', title: 'Nettoyage en cours...' };
    case 'error':
      return { label: 'Échec - Réessayer', title: 'Échec (ffmpeg manquant ?) - Réessayer' };
    default:
      return {
        label: 'Nettoyer le souffle',
        title: 'Nettoyer le souffle/bruit de fond (traitement en arrière-plan)'
      };
  }
};

type Panel = 'match' | 'edit' | null;

const BookDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const detail = useBookDetail(id);
  const { book, busy } = detail;
  const [panel, setPanel] = useState<Panel>(null);

  const togglePanel = (target: Exclude<Panel, null>) =>
    setPanel((current) => (current === target ? null : target));

  const backButton = (
    <button type="button" className="bd-back" onClick={() => navigate(-1)}>
      <ArrowLeft size={20} aria-hidden="true" /> Retour
    </button>
  );

  if (detail.loading) {
    return (
      <div className="page-content">
        {backButton}
        <div className="bd-empty" role="status">Chargement...</div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="page-content">
        {backButton}
        <div className="bd-empty">Audiolive non trouvé</div>
      </div>
    );
  }

  const cleaning = busy.startingCleanAudio || busy.togglingCleanedAudio || book.noise_reduction_status === 'processing';
  const cleanAudio = describeCleanAudio(book);
  const hasSeries = Boolean(book.series);

  return (
    <div className="page-content">
      {backButton}

      <div className="bd-hero book-hero">
        <div className="book-hero-cover">
          {book.cover_url ? (
            <CoverImage
              bookId={book.id}
              coverUrl={book.cover_url}
              alt={book.title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div className="bd-cover-placeholder" aria-hidden="true">📚</div>
          )}
        </div>

        <div className="bd-hero-info">
          <h1 className="page-title">{book.title}</h1>
          <p className={`bd-author ${hasSeries ? 'has-series' : ''}`}>par {book.author}</p>
          {hasSeries && (
            <p className="bd-series">
              Série : {book.series}
              {book.series_sequence != null && book.series_sequence !== '' && ` (Tome ${book.series_sequence})`}
            </p>
          )}
          {book.narrator && <p className="bd-author">Narrateur : {book.narrator}</p>}

          <div className="bd-fact">
            <p className="bd-fact-label">Durée</p>
            <p className="bd-fact-value">{formatDuration(book.duration)}</p>
          </div>

          {book.progress.percentage > 0 && (
            <div className="bd-fact">
              <p className="bd-fact-label">Progression</p>
              <div
                className="bd-progress"
                role="progressbar"
                aria-label="Progression de lecture"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(book.progress.percentage)}
              >
                <div className="bd-progress-fill" style={{ width: `${book.progress.percentage}%` }} />
              </div>
              <p className="bd-progress-caption">{book.progress.percentage.toFixed(1)}% complété</p>
            </div>
          )}

          <div className="bd-actions">
            <ExpandAction variant="primary" label="Lire" icon={<Play size={18} />} onClick={() => detail.play()} />
            <ExpandAction label="Associer" icon={<Search size={16} />} onClick={() => togglePanel('match')} />
            <ExpandAction label="Modifier" icon={<Pencil size={16} />} onClick={() => togglePanel('edit')} />
            <ExpandAction
              variant={book.is_finished ? 'confirmed' : undefined}
              label={book.is_finished ? 'Lu' : 'Marquer comme lu'}
              icon={busy.togglingFinished ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
              disabled={busy.togglingFinished}
              onClick={detail.toggleFinished}
            />
            <ExpandAction
              variant={book.noise_reduction_status === 'done' && book.use_cleaned_audio ? 'confirmed' : undefined}
              label={cleanAudio.label}
              title={cleanAudio.title}
              icon={
                cleaning ? <Loader2 size={16} className="spin" />
                : book.noise_reduction_status === 'done' && book.use_cleaned_audio ? <CheckCircle2 size={16} />
                : <Sparkles size={16} />
              }
              disabled={cleaning}
              // Once cleaned, clicking flips between the cleaned and original
              // audio instead of re-running the pass - the cleaned files stay
              // cached, so this is instant either way.
              onClick={book.noise_reduction_status === 'done' ? detail.toggleUseCleanedAudio : detail.cleanAudio}
            />
          </div>

          {panel === 'match' && (
            <MatchPanel
              book={book}
              onApplied={async () => {
                setPanel(null);
                await detail.refresh();
              }}
            />
          )}

          {panel === 'edit' && (
            <EditForm
              book={book}
              onChanged={detail.refresh}
              onSaved={async () => {
                setPanel(null);
                await detail.refresh();
              }}
            />
          )}

          {book.manual_overrides && book.manual_overrides.length > 0 && (
            <p className="bd-locked-note">
              <Lock size={11} aria-hidden="true" /> Modifié manuellement, protégé des prochaines synchronisations (ouvrir "Modifier" pour déverrouiller un champ)
            </p>
          )}
        </div>
      </div>

      {book.description && (
        <section className="bd-section">
          <h2 className="bd-heading">Description</h2>
          <p className="bd-description">{book.description}</p>
        </section>
      )}

      <BookmarkList
        book={book}
        resumingBookmarkId={busy.resumingBookmarkId}
        onResume={detail.resumeBookmark}
        onRename={detail.renameBookmark}
        onDelete={detail.deleteBookmark}
      />

      <ChapterList
        book={book}
        activeChapterIndex={detail.activeChapterIndex}
        activePosition={detail.activePosition}
        onPlayChapter={detail.play}
      />
    </div>
  );
};

export default BookDetailPage;
