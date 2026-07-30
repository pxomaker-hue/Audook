import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, ListMusic, Bookmark, Loader2, Check, PictureInPicture2, MoreHorizontal, ArrowLeft, Gauge, SlidersHorizontal, AudioLines } from 'lucide-react';
import { usePlayerState as useDesktopPlayerState, formatTime } from '../hooks/usePlayerState';
import { usePlayerState as useMobilePlayerState } from '../hooks/useMobilePlayerState';
import PlayerMoreMenu from './PlayerMoreMenu';
import VolumeControl from './VolumeControl';

import { isCapacitorPlatform } from '../native/platform';
import { useCoverBlobUrl } from '../hooks/useCoverBlobUrl';
import { expandedPlayerStore, useExpandedPlayer } from '../native/expandedPlayerStore';

// Mirrors the window.electron?.miniPlayer capability-check pattern used
// elsewhere in this file.
const usePlayerState = isCapacitorPlatform ? useMobilePlayerState : useDesktopPlayerState;

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

  const coverSrc = useCoverBlobUrl(state.currentBook?.id ?? '', state.currentBook?.cover_url);

  // Compact bar's own "..." menu (bookmark + chapters) - separate from
  // PlayerMoreMenu (speed/equalizer/loudness/cast), which the compact bar
  // never had room for and mobile doesn't implement yet anyway (see
  // useMobilePlayerState.ts's no-op handlers).
  const [showCompactMenu, setShowCompactMenu] = useState(false);
  const compactMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showCompactMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (compactMenuRef.current && !compactMenuRef.current.contains(e.target as Node)) {
        setShowCompactMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showCompactMenu]);

  // Mobile-only full-screen player - separate "..." menu instance from the
  // compact bar's (both are mounted at once, CSS just picks which shows).
  const isExpanded = useExpandedPlayer();
  const [showExpandedMenu, setShowExpandedMenu] = useState(false);
  const expandedMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showExpandedMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (expandedMenuRef.current && !expandedMenuRef.current.contains(e.target as Node)) {
        setShowExpandedMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExpandedMenu]);

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
      loudnessNormalizationEnabled={state.loudnessNormalizationEnabled}
      onToggleLoudnessNormalization={handleToggleLoudnessNormalization}
      compressionPreset={state.compressionPreset}
      onCycleCompression={handleCycleCompression}
      volume={state.volume}
      onVolumeChange={handleVolumeChange}
      showVolume={false}
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
    <div className={`player ${isCapacitorPlatform && isExpanded ? 'player-mobile-expanded' : ''}`}>
      {/* Full docked layout - visible above the compact breakpoint (see
          App.css). Rendering both variants and letting CSS pick which one
          shows (instead of a JS matchMedia state) avoids the two ever
          getting out of sync with the real viewport width. */}
      <div className="player-full">
        <div className="player-title-bar">
          {isCapacitorPlatform && (
            <button
              className="player-button player-back-button"
              onClick={() => expandedPlayerStore.setExpanded(false)}
              title="Retour"
            >
              <ArrowLeft size={18} />
            </button>
          )}
          <span className="player-title-bar-text">{state.currentBook.title}</span>
        </div>

        <div
          className="player-cover-wrap"
          onClick={() => navigate(`/book/${state.currentBook.id}`)}
          style={{ cursor: 'pointer' }}
          title="Voir la page du livre"
        >
          {coverSrc && (
            <div
              className="player-cover-glow"
              style={{ backgroundImage: `url(${coverSrc})` }}
            />
          )}
          <div className="player-cover">
            {coverSrc ? (
              <img src={coverSrc} alt={state.currentBook.title} />
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

        {isCapacitorPlatform ? (
          // Mobile full-screen layout: chapters, prev, -30s, play/pause,
          // +30s, next, then a single "..." for the rest (just bookmark -
          // speed/eq/loudness/compression/volume/cast are still no-ops on
          // mobile's native player, see useMobilePlayerState.ts).
          <div className="player-controls player-controls-mobile-full">
            {chaptersButton(16)}
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
              className={`player-button main ${state.isPlaying ? 'playing' : ''}`}
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

            <div className="more-menu-wrapper" ref={expandedMenuRef}>
              {showExpandedMenu && (
                <div className="more-menu-popover">
                  <div className="more-menu-row">
                    <span className="more-menu-label">Marque-page</span>
                    <button
                      className={`player-button more-menu-icon ${bookmarkAdded ? 'confirmed' : ''}`}
                      onClick={handleAddBookmark}
                      disabled={addingBookmark || bookmarkAdded || state.currentChapterIndex === null}
                      title="Marquer la position actuelle"
                    >
                      {addingBookmark ? <Loader2 size={16} className="spin" /> : bookmarkAdded ? <Check size={16} /> : <Bookmark size={16} />}
                    </button>
                  </div>
                  <div className="more-menu-row">
                    <span className="more-menu-label">Vitesse ({state.speed}x)</span>
                    <button className="player-button more-menu-icon" onClick={handleCycleSpeed} title="Vitesse de lecture">
                      <Gauge size={16} />
                    </button>
                  </div>
                  <div className="more-menu-row">
                    <span className="more-menu-label">
                      Égaliseur{state.equalizerPresetId ? ` (${equalizerPresets.find((p) => p.id === state.equalizerPresetId)?.name ?? ''})` : ' (désactivé)'}
                    </span>
                    <button className="player-button more-menu-icon" onClick={handleCycleEqualizer} title="Égaliseur">
                      <SlidersHorizontal size={16} />
                    </button>
                  </div>
                  <div className="more-menu-row">
                    <span className="more-menu-label">Normalisation du volume</span>
                    <button
                      className={`player-button more-menu-icon ${state.loudnessNormalizationEnabled ? 'confirmed' : ''}`}
                      onClick={handleToggleLoudnessNormalization}
                      title="Normalisation du volume (par livre)"
                    >
                      <AudioLines size={16} />
                    </button>
                  </div>
                </div>
              )}
              <button className="player-button" onClick={() => setShowExpandedMenu((v) => !v)} title="Plus d'options">
                <MoreHorizontal size={16} />
              </button>
            </div>
          </div>
        ) : (
          <>
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
                className={`player-button main ${state.isPlaying ? 'playing' : ''}`}
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
          </>
        )}
      </div>

      {/* Compact horizontal bar - visible below the compact breakpoint.
          Two rows: cover + progress/timecodes on top, playback controls +
          a "..." menu (bookmark/chapters) below - the old single-row
          layout crammed cover+title+5 controls+5 more buttons into one
          line and overflowed ~530px of content into a ~350px bar. */}
      <div className={`player-compact-view ${isCapacitorPlatform ? 'player-compact-view-mobile' : ''}`}>
        {isCapacitorPlatform ? (
          // Mobile: cover tap expands to the full-screen player (see
          // .player-mobile-expanded above) rather than navigating away, and
          // controls get their own dedicated "..." menu - a phone screen is
          // permanently this narrow, unlike desktop's occasionally-resized
          // window, so this needs to hold up on its own rather than share
          // desktop's single-row layout below.
          <>
            <div className="player-compact-row1">
              <div
                className="player-cover-wrap player-cover-wrap-tappable"
                onClick={() => expandedPlayerStore.setExpanded(true)}
                title="Agrandir le lecteur"
              >
                {coverSrc ? (
                  <img src={coverSrc} alt={state.currentBook.title} />
                ) : (
                  <span>📚</span>
                )}
              </div>

              <div className="player-compact-progress">
                <div className="progress-bar" onClick={handleSeek}>
                  <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
                </div>
                <div className="player-time-row compact">
                  <span className="player-time">{formatTime(state.position)}</span>
                  <span className="player-time">{formatTime(state.duration)}</span>
                </div>
              </div>
            </div>

            <div className="player-compact-row2">
              <div className="player-controls">
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
              </div>

              <div className="more-menu-wrapper" ref={compactMenuRef}>
                {showCompactMenu && (
                  <div className="more-menu-popover">
                    <div className="more-menu-row">
                      <span className="more-menu-label">Marque-page</span>
                      <button
                        className={`player-button more-menu-icon ${bookmarkAdded ? 'confirmed' : ''}`}
                        onClick={handleAddBookmark}
                        disabled={addingBookmark || bookmarkAdded || state.currentChapterIndex === null}
                        title="Marquer la position actuelle"
                      >
                        {addingBookmark ? <Loader2 size={16} className="spin" /> : bookmarkAdded ? <Check size={16} /> : <Bookmark size={16} />}
                      </button>
                    </div>
                    <div className="more-menu-row">
                      <span className="more-menu-label">Chapitres</span>
                      <button
                        className="player-button more-menu-icon"
                        onClick={() => navigate(`/book/${state.currentBook.id}`)}
                        title="Voir les chapitres"
                      >
                        <ListMusic size={16} />
                      </button>
                    </div>
                  </div>
                )}
                <button className="player-button" onClick={() => setShowCompactMenu(v => !v)} title="Plus d'options">
                  <MoreHorizontal size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <div
              className="player-cover-wrap"
              onClick={() => navigate(`/book/${state.currentBook.id}`)}
              style={{ cursor: 'pointer' }}
              title="Voir la page du livre"
            >
              {coverSrc ? (
                <img src={coverSrc} alt={state.currentBook.title} />
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
            </div>

            <div className="player-extra-row compact">
              {bookmarkButton(14)}
              {chaptersButton(14)}
              {moreMenu(14)}
              {volumeControl(14)}
              {miniPlayerButton(14)}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Player;
