import React from 'react';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, Minimize2, Bookmark, Loader2, Check } from 'lucide-react';
import { usePlayerState, formatTime } from '../hooks/usePlayerState';
import PlayerMoreMenu from './PlayerMoreMenu';
import { useCoverBlobUrl } from '../hooks/useCoverBlobUrl';

// Rendered in the detached mini-player Electron window (see electron/main.js
// createMiniWindow, loaded at the '#/mini' hash route). Deliberately shows
// only the player, nothing else - the whole point is a small always-on-top
// widget instead of the full library window.
const MiniPlayerView: React.FC = () => {
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
    handleToggleLoudnessNormalization,
    handleCycleCompression,
    handleCycleSleepTimer,
    castDevices,
    castScanning,
    castConnecting,
    handleScanCastDevices,
    handleConnectCastDevice,
    handleDisconnectCastDevice,
    SEEK_STEP_SECONDS
  } = usePlayerState();

  const percentage = state.duration ? (state.position / state.duration) * 100 : 0;
  const coverSrc = useCoverBlobUrl(state.currentBook?.id ?? '', state.currentBook?.cover_url);

  return (
    <div className="mini-player">
      <div className="mini-player-drag-region">
        <button
          className="player-button"
          onClick={() => window.electron?.miniPlayer.deactivate()}
          title="Revenir à la fenêtre principale"
        >
          <Minimize2 size={14} />
        </button>
      </div>

      {!state.currentBook ? (
        <div className="mini-player-empty">Aucune lecture en cours</div>
      ) : (
        <>
          <div className="mini-player-body">
            <div className="mini-player-cover-wrap">
              {coverSrc ? (
                <img src={coverSrc} alt={state.currentBook.title} />
              ) : (
                <span>📚</span>
              )}
            </div>
            <div className="mini-player-info">
              <div className="mini-player-title">{state.currentBook.title}</div>
              <div className="mini-player-subtitle">{state.currentBook.author}</div>
              {state.currentChapterTitle && (
                <div className="mini-player-subtitle">{state.currentChapterTitle}</div>
              )}
            </div>
          </div>

          <div className="progress-bar" onClick={handleSeek}>
            <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
          </div>
          <div className="player-time-row">
            <span className="player-time">{formatTime(state.position)}</span>
            <span className="player-time">{formatTime(state.duration)}</span>
          </div>

          <div className="player-controls">
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
            <button className="player-button" onClick={handlePreviousClick} title="Chapitre précédent / Redémarrer">
              <SkipBack size={14} />
            </button>
            <button className="player-button" onClick={() => handleSeekStep(-SEEK_STEP_SECONDS)} title="Reculer de 30s">
              <Rewind size={14} />
            </button>
            <button
              className={`player-button main ${state.isPlaying ? 'playing' : ''}`}
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
            <PlayerMoreMenu
              speed={state.speed}
              onCycleSpeed={handleCycleSpeed}
              equalizerPresetId={state.equalizerPresetId}
              equalizerPresets={equalizerPresets}
              onCycleEqualizer={handleCycleEqualizer}
              loudnessNormalizationEnabled={state.loudnessNormalizationEnabled}
              onToggleLoudnessNormalization={handleToggleLoudnessNormalization}
              compressionPreset={state.compressionPreset}
              onCycleCompression={handleCycleCompression}
              volume={state.volume}
              onVolumeChange={handleVolumeChange}
              sleepTimerRemainingSeconds={state.sleepTimerRemainingSeconds}
              onCycleSleepTimer={handleCycleSleepTimer}
              isCasting={state.isCasting}
              castDeviceName={state.castDeviceName}
              castDevices={castDevices}
              castScanning={castScanning}
              castConnecting={castConnecting}
              onScanCast={handleScanCastDevices}
              onConnectCast={handleConnectCastDevice}
              onDisconnectCast={handleDisconnectCastDevice}
              buttonSize={14}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default MiniPlayerView;
