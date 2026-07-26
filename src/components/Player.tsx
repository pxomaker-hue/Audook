import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, ListMusic, Volume1, Volume2, VolumeX, Bookmark, Loader2, Check, PictureInPicture2 } from 'lucide-react';
import { usePlayerState, formatTime } from '../hooks/usePlayerState';
import PlayerMoreMenu from './PlayerMoreMenu';

// Below this window width the full side-panel player no longer fits (it used
// to just disappear entirely) - switch to a compact horizontal bar instead.
const COMPACT_BREAKPOINT = '(max-width: 1100px)';

// Stable pseudo-random bar heights for the waveform decoration
const WAVE_BARS = Array.from({ length: 32 }, (_, i) => {
  const seed = Math.sin(i * 12.9898) * 43758.5453;
  return 8 + Math.round((seed - Math.floor(seed)) * 24);
});

const VolumeIcon = ({ volume }: { volume: number }) => {
  if (volume === 0) return <VolumeX size={16} />;
  if (volume < 50) return <Volume1 size={16} />;
  return <Volume2 size={16} />;
};

const Player: React.FC = () => {
  const navigate = useNavigate();
  const {
    state,
    showVolume,
    setShowVolume,
    addingBookmark,
    bookmarkAdded,
    volumeWrapperRef,
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
  const [compact, setCompact] = useState(() => window.matchMedia(COMPACT_BREAKPOINT).matches);

  useEffect(() => {
    const mql = window.matchMedia(COMPACT_BREAKPOINT);
    const checkCompact = () => setCompact(mql.matches);
    mql.addEventListener('change', checkCompact);
    // Belt and suspenders: also recheck on the raw resize event, in case
    // `change` doesn't fire reliably (seen with some window-resize sources).
    window.addEventListener('resize', checkCompact);
    return () => {
      mql.removeEventListener('change', checkCompact);
      window.removeEventListener('resize', checkCompact);
    };
  }, []);

  if (!state.currentBook) {
    return (
      <div className={`player ${compact ? 'compact' : ''}`}>
        <div className="player-empty">Sélectionnez un livre pour commencer</div>
      </div>
    );
  }

  const percentage = state.duration ? (state.position / state.duration) * 100 : 0;

  if (compact) {
    return (
      <div className="player compact">
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
          <button
            className={`player-button ${bookmarkAdded ? 'confirmed' : ''}`}
            onClick={handleAddBookmark}
            disabled={addingBookmark || bookmarkAdded || state.currentChapterIndex === null}
            title={state.currentChapterIndex === null ? 'Lancez la lecture pour marquer la position actuelle' : 'Marquer la position actuelle'}
          >
            {addingBookmark ? (
              <Loader2 size={14} className="spin" />
            ) : bookmarkAdded ? (
              <Check size={14} />
            ) : (
              <Bookmark size={14} />
            )}
          </button>
          <div className="volume-popover-wrapper" ref={volumeWrapperRef}>
            {showVolume && (
              <div className="volume-popover">
                <input
                  type="range"
                  className="volume-slider-vertical"
                  min="0"
                  max="100"
                  value={state.volume}
                  onChange={(e) => handleVolumeChange(parseInt(e.target.value))}
                />
              </div>
            )}
            <button
              className="player-button"
              onClick={() => setShowVolume(!showVolume)}
              title="Volume"
            >
              <VolumeIcon volume={state.volume} />
            </button>
          </div>
          {window.electron?.miniPlayer && (
            <button
              className="player-button"
              onClick={() => window.electron?.miniPlayer.activate()}
              title="Détacher le mini-lecteur"
            >
              <PictureInPicture2 size={14} />
            </button>
          )}
          <button
            className="player-button"
            onClick={() => navigate(`/book/${state.currentBook.id}`)}
            title="Voir les chapitres"
          >
            <ListMusic size={14} />
          </button>
          <PlayerMoreMenu
            speed={state.speed}
            onCycleSpeed={handleCycleSpeed}
            equalizerPresetId={state.equalizerPresetId}
            equalizerPresets={equalizerPresets}
            onCycleEqualizer={handleCycleEqualizer}
            normalizationEnabled={state.normalizationEnabled}
            onToggleNormalization={handleToggleNormalization}
            buttonSize={14}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="player">
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
        <button
          className={`player-button ${bookmarkAdded ? 'confirmed' : ''}`}
          onClick={handleAddBookmark}
          disabled={addingBookmark || bookmarkAdded || state.currentChapterIndex === null}
          title={state.currentChapterIndex === null ? 'Lancez la lecture pour marquer la position actuelle' : 'Marquer la position actuelle'}
        >
          {addingBookmark ? (
            <Loader2 size={16} className="spin" />
          ) : bookmarkAdded ? (
            <Check size={16} />
          ) : (
            <Bookmark size={16} />
          )}
        </button>
        <button
          className="player-button"
          onClick={() => navigate(`/book/${state.currentBook.id}`)}
          title="Voir les chapitres"
        >
          <ListMusic size={16} />
        </button>
        <div className="volume-popover-wrapper" ref={volumeWrapperRef}>
          {showVolume && (
            <div className="volume-popover">
              <input
                type="range"
                className="volume-slider-vertical"
                min="0"
                max="100"
                value={state.volume}
                onChange={(e) => handleVolumeChange(parseInt(e.target.value))}
              />
            </div>
          )}
          <button
            className="player-button"
            onClick={() => setShowVolume(!showVolume)}
            title="Volume"
          >
            <VolumeIcon volume={state.volume} />
          </button>
        </div>
        {window.electron?.miniPlayer && (
          <button
            className="player-button"
            onClick={() => window.electron?.miniPlayer.activate()}
            title="Détacher le mini-lecteur"
          >
            <PictureInPicture2 size={16} />
          </button>
        )}
        <PlayerMoreMenu
          speed={state.speed}
          onCycleSpeed={handleCycleSpeed}
          equalizerPresetId={state.equalizerPresetId}
          equalizerPresets={equalizerPresets}
          onCycleEqualizer={handleCycleEqualizer}
          normalizationEnabled={state.normalizationEnabled}
          onToggleNormalization={handleToggleNormalization}
        />
      </div>
    </div>
  );
};

export default Player;
