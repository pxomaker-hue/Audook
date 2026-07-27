import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, ListMusic, Bookmark, Loader2, Check, PictureInPicture2 } from 'lucide-react';
import { usePlayerState, formatTime } from '../hooks/usePlayerState';
import PlayerMoreMenu from './PlayerMoreMenu';
import VolumeControl from './VolumeControl';

// Stable pseudo-random bar heights for the waveform decoration
const WAVE_BARS = Array.from({ length: 32 }, (_, i) => {
  const seed = Math.sin(i * 12.9898) * 43758.5453;
  return 8 + Math.round((seed - Math.floor(seed)) * 24);
});

const Player: React.FC = () => {
  const navigate = useNavigate();
  const {
    state,
    addingBookmark,
    bookmarkAdded,
    handlePlayPause,
    handlePreviousClick,
    handleNextClick,
    handleSeek,
    handleSeekStep,
    handleVolumeChange,
    handleAddBookmark,
    handleCycleSpeed,
    equalizerPresets,
    handleCycleEqualizer,
    handleToggleNormalization,
    SEEK_STEP_SECONDS
  } = usePlayerState();

  if (!state.currentBook) {
    return (
      <div className="player">
        <div className="player-empty">Sélectionnez un livre pour commencer</div>
      </div>
    );
  }

  const percentage = state.duration ? (state.position / state.duration) * 100 : 0;

  const moreMenu = (buttonSize?: number) => (
    <PlayerMoreMenu
      speed={state.speed}
      onCycleSpeed={handleCycleSpeed}
      equalizerPresetId={state.equalizerPresetId}
      equalizerPresets={equalizerPresets}
      onCycleEqualizer={handleCycleEqualizer}
      normalizationEnabled={state.normalizationEnabled}
      onToggleNormalization={handleToggleNormalization}
      buttonSize={buttonSize}
    />
  );

  const bookmarkButton = (size: number) => (
    <button
      className={`player-button ${bookmarkAdded ? 'confirmed' : ''}`}
      onClick={handleAddBookmark}
      disabled={addingBookmark || bookmarkAdded || state.currentChapterIndex === null}
      title={state.currentChapterIndex === null ? 'Lancez la lecture pour marquer la position actuelle' : 'Marquer la position actuelle'}
    >
      {addingBookmark ? (
        <Loader2 size={size} className="spin" />
      ) : bookmarkAdded ? (
        <Check size={size} />
      ) : (
        <Bookmark size={size} />
      )}
    </button>
  );

  const chaptersButton = (size: number) => (
    <button
      className="player-button"
      onClick={() => navigate(`/book/${state.currentBook.id}`)}
      title="Voir les chapitres"
    >
      <ListMusic size={size} />
    </button>
  );

  const volumeControl = (size: number) => (
    <VolumeControl volume={state.volume} onChange={handleVolumeChange} size={size} />
  );

  const miniPlayerButton = (size: number) =>
    window.electron?.miniPlayer && (
      <button
        className="player-button"
        onClick={() => window.electron?.miniPlayer.activate()}
        title="Détacher le mini-lecteur"
      >
        <PictureInPicture2 size={size} />
      </button>
    );

  return (
    <div className="player">
      {/* Full docked layout - visible above the compact breakpoint (see
          App.css). Rendering both variants and letting CSS pick which one
          shows (instead of a JS matchMedia state) avoids the two ever
          getting out of sync with the real viewport width. */}
      <div className="player-full">
        <div className="player-title-bar">{state.currentBook.title}</div>

        <div className="player-cover-wrap">
          {state.currentBook.cover_url && (
            <div
              className="player-cover-glow"
              style={{ backgroundImage: `url(${state.currentBook.cover_url})` }}
            />
          )}
          <div className="player-cover">
            {state.currentBook.cover_url ? (
              <img src={state.currentBook.cover_url} alt={state.currentBook.title} />
            ) : (
              <span>📚</span>
            )}
          </div>
        </div>

        {state.currentChapterTitle && (
          <div className="player-current-chapter">{state.currentChapterTitle}</div>
        )}
        <div className="player-author">{state.currentBook.author}</div>

        {state.currentBook.description && (
          <div className="player-description">{state.currentBook.description}</div>
        )}

        <div className={`player-waveform ${state.isPlaying ? 'playing' : ''}`}>
          {WAVE_BARS.map((h, i) => (
            <span key={i} style={{ height: `${h}px` }} />
          ))}
        </div>

        <div className="player-progress">
          <div className="progress-bar" onClick={handleSeek}>
            <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
          </div>
          <div className="player-time-row">
            <span className="player-time">{formatTime(state.position)}</span>
            <span className="player-time">{formatTime(state.duration)}</span>
          </div>
        </div>

        <div className="player-controls">
          <button
            className="player-button"
            onClick={handlePreviousClick}
            title="Chapitre précédent (2 clics) / Redémarrer le chapitre (1 clic)"
          >
            <SkipBack size={16} />
          </button>
          <button className="player-button" onClick={() => handleSeekStep(-SEEK_STEP_SECONDS)} title="Reculer de 30s">
            <Rewind size={16} />
          </button>
          <button
            className="player-button main"
            onClick={handlePlayPause}
            title={state.isPlaying ? 'Pause' : 'Lecture'}
          >
            {state.isPlaying ? <Pause size={22} /> : <Play size={22} />}
          </button>
          <button className="player-button" onClick={() => handleSeekStep(SEEK_STEP_SECONDS)} title="Avancer de 30s">
            <FastForward size={16} />
          </button>
          <button className="player-button" onClick={handleNextClick} title="Chapitre suivant">
            <SkipForward size={16} />
          </button>
        </div>

        <div className="player-extra-row">
          {bookmarkButton(16)}
          {chaptersButton(16)}
          {moreMenu()}
          {volumeControl(16)}
          {miniPlayerButton(16)}
        </div>
      </div>

      {/* Compact horizontal bar - visible below the compact breakpoint. */}
      <div className="player-compact-view">
        <div className="player-cover-wrap">
          {state.currentBook.cover_url ? (
            <img src={state.currentBook.cover_url} alt={state.currentBook.title} />
          ) : (
            <span>📚</span>
          )}
        </div>

        <div className="player-compact-info">
          <div className="player-compact-title">
            {state.currentChapterTitle || state.currentBook.title}
          </div>
          <div className="player-compact-subtitle">{state.currentBook.author}</div>
          <div className="progress-bar" onClick={handleSeek}>
            <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
          </div>
        </div>

        <div className="player-controls">
          <button className="player-button" onClick={handlePreviousClick} title="Chapitre précédent / Redémarrer">
            <SkipBack size={14} />
          </button>
          <button className="player-button" onClick={() => handleSeekStep(-SEEK_STEP_SECONDS)} title="Reculer de 30s">
            <Rewind size={14} />
          </button>
          <button
            className="player-button main"
            onClick={handlePlayPause}
            title={state.isPlaying ? 'Pause' : 'Lecture'}
          >
            {state.isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <button className="player-button" onClick={() => handleSeekStep(SEEK_STEP_SECONDS)} title="Avancer de 30s">
            <FastForward size={14} />
          </button>
          <button className="player-button" onClick={handleNextClick} title="Chapitre suivant">
            <SkipForward size={14} />
          </button>
        </div>

        <div className="player-extra-row compact">
          {bookmarkButton(14)}
          {chaptersButton(14)}
          {moreMenu(14)}
          {volumeControl(14)}
          {miniPlayerButton(14)}
        </div>
      </div>
    </div>
  );
};

export default Player;
