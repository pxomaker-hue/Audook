import axios from 'axios';
import AudookPlayer from './AudookPlayer';
import { getApiBase } from '../config';

// Singleton playback state for the mobile (Capacitor) player, independent of
// React's component tree - HomePage/BookDetailPage/AuthorPage all need to
// trigger playback on the same native player instance regardless of which
// component is currently mounted, and useMobilePlayerState (the hook
// components read from) just subscribes to this store.

export interface EqualizerPreset {
  id: string;
  name: string;
  bands: number[];
  preamp: number;
  is_builtin: boolean;
}

export interface MobilePlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  currentChapterIndex: number;
  position: number; // seconds
  duration: number; // seconds
  speed: number;
  equalizerPresetId: string | null;
  loudnessNormalizationEnabled: boolean;
  compressionPreset: string | null;
}

// Same cycle/keys as PlayerService.COMPRESSION_STEPS in
// app/services/player_service.py - off -> léger -> modéré -> fort -> off.
const COMPRESSION_STEPS: (string | null)[] = [null, 'leger', 'modere', 'fort'];

const PROGRESS_PUSH_INTERVAL_MS = 15000;
// If the backend hasn't measured a book's loudness gain yet, one retry
// after this delay is usually enough (the ffmpeg analysis only samples the
// first 10 minutes of audio) - see get_book_loudness_gain in audook_backend.py.
const LOUDNESS_GAIN_RETRY_MS = 5000;

let state: MobilePlayerState = {
  isPlaying: false,
  currentBook: null,
  currentChapterIndex: 0,
  position: 0,
  duration: 0,
  speed: 1,
  equalizerPresetId: null,
  loudnessNormalizationEnabled: false,
  compressionPreset: null
};

// Fetched lazily once and cached - the actual band/preamp values used to
// build the Android Equalizer effect (see AudookPlayerPlugin.kt), same
// presets desktop's VLC equalizer applies.
let equalizerPresets: EqualizerPreset[] | null = null;

const listeners = new Set<(s: MobilePlayerState) => void>();
let progressInterval: ReturnType<typeof setInterval> | null = null;
let listenersRegistered = false;

function setState(patch: Partial<MobilePlayerState>) {
  state = { ...state, ...patch };
  listeners.forEach(l => l(state));
}

function ensureNativeListeners() {
  if (listenersRegistered) return;
  listenersRegistered = true;

  AudookPlayer.addListener('positionUpdate', (data) => {
    setState({ position: data.positionMs / 1000, duration: data.durationMs / 1000 });
  });
  AudookPlayer.addListener('stateChange', (data) => {
    setState({ isPlaying: data.isPlaying });
  });
  // Fires for every chapter change ExoPlayer makes on its own within the
  // playlist handed to it in play() below - including auto-advancing past
  // the end of a chapter, which now happens natively regardless of whether
  // the WebView is active. Previously the JS side only learned "a chapter
  // ended" via the 'ended' event and had to decide + start the next one
  // itself, which never ran while the app was backgrounded/screen off,
  // silently stopping playback at every chapter boundary.
  AudookPlayer.addListener('chapterChanged', (data) => {
    const book = state.currentBook;
    const duration = book?.chapters?.[data.chapterIndex]?.duration || 0;
    setState({ currentChapterIndex: data.chapterIndex, position: 0, duration });
  });
  // Only fires once the very last chapter in the playlist finishes - every
  // earlier chapter boundary is now a 'chapterChanged' event instead (see
  // above), not this one.
  AudookPlayer.addListener('ended', () => {
    pushProgress(true);
    stopProgressPushLoop();
  });
}

function pushProgress(finished = false) {
  const book = state.currentBook;
  if (!book) return;
  axios
    .post(`${getApiBase()}/books/${book.id}/progress`, {
      chapter_index: state.currentChapterIndex,
      position_seconds: state.position
    })
    .catch(error => console.error('Failed to push mobile progress:', error));
  if (finished) {
    // Best effort: let the backend's own >=99% threshold handle "finished",
    // this just guarantees one last push right at chapter end.
  }
}

function startProgressPushLoop() {
  if (progressInterval) return;
  progressInterval = setInterval(() => pushProgress(), PROGRESS_PUSH_INTERVAL_MS);
}

function stopProgressPushLoop() {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

// The whole book's chapters are sent to the native side as one playlist -
// see AudookPlayer.ts/AudookPlayerPlugin.kt - so ExoPlayer can advance
// through every chapter entirely on its own from here on. Chapter
// navigation (goToNextChapter/goToPreviousChapter below) no longer calls
// this again; it just moves within the already-loaded playlist natively.
async function play(book: any, chapterIndex?: number, positionSeconds?: number) {
  ensureNativeListeners();
  const idx = chapterIndex ?? 0;
  const pos = positionSeconds ?? 0;
  const chapters = book.chapters || [];
  if (!chapters.length) return;

  const playlist = chapters.map((chapter: any) => ({
    url: `${getApiBase()}/cast/local-audio?path=${encodeURIComponent(chapter.audio_file)}`,
    title: chapter.title || book.title
  }));

  setState({
    currentBook: book,
    currentChapterIndex: idx,
    position: pos,
    duration: chapters[idx]?.duration || 0
  });

  // The resume position goes straight into play() (native side passes it to
  // ExoPlayer's setMediaItems) rather than a separate seek() call right
  // after - a seek issued that early could arrive before the player
  // finished loading the item and get silently dropped once it became
  // ready, which is why resuming a book on mobile always restarted from 0.
  await AudookPlayer.play({
    chapters: playlist,
    startIndex: idx,
    cover: book.cover_url || undefined,
    positionMs: pos > 0 ? pos * 1000 : undefined
  });
  // PlaybackParameters/audio effects live on the player itself, not the
  // media item, so they should already carry over across chapters within
  // one playlist - but a fresh play() call rebuilds the whole playlist from
  // scratch, which on a cold app start means a MediaController that's never
  // had these applied yet. Re-asserting them here keeps the chosen
  // speed/equalizer across "start listening to a different book" too, not
  // just chapter transitions.
  if (state.speed !== 1) {
    await AudookPlayer.setSpeed({ speed: state.speed });
  }
  if (state.equalizerPresetId) {
    const preset = (equalizerPresets || []).find((p) => p.id === state.equalizerPresetId);
    if (preset) {
      await AudookPlayer.setEqualizer({ bands: preset.bands, preamp: preset.preamp });
    }
  }
  if (state.compressionPreset) {
    await AudookPlayer.setCompression({ preset: state.compressionPreset });
  }
  // Unlike speed/equalizer (global preferences), loudness gain is specific
  // to whichever book is now playing - always re-fetch/apply it for the
  // new book rather than carrying over the previous book's gain.
  if (state.loudnessNormalizationEnabled) {
    applyLoudnessGainForBook(book.id);
  } else {
    await AudookPlayer.setLoudnessGain({ gainDb: 0 });
  }
  startProgressPushLoop();
}

async function setSpeed(speed: number) {
  setState({ speed });
  await AudookPlayer.setSpeed({ speed });
}

async function fetchEqualizerPresets(): Promise<EqualizerPreset[]> {
  if (equalizerPresets) return equalizerPresets;
  try {
    const response = await axios.get(`${getApiBase()}/equalizer/presets`);
    equalizerPresets = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Failed to fetch equalizer presets:', error);
    equalizerPresets = [];
  }
  return equalizerPresets;
}

// Cycles null (off) -> each preset in turn -> back to null, mirroring
// desktop's /api/player/equalizer/cycle - applied locally here instead of
// through the backend's VLC session, which mobile never plays through.
async function cycleEqualizer(): Promise<string | null> {
  const presets = await fetchEqualizerPresets();
  const ids: (string | null)[] = [null, ...presets.map((p) => p.id)];
  const currentIndex = ids.indexOf(state.equalizerPresetId);
  const nextId = ids[(currentIndex + 1) % ids.length];
  setState({ equalizerPresetId: nextId });

  if (nextId === null) {
    await AudookPlayer.setEqualizer({ bands: null });
  } else {
    const preset = presets.find((p) => p.id === nextId);
    if (preset) {
      await AudookPlayer.setEqualizer({ bands: preset.bands, preamp: preset.preamp });
    }
  }
  return nextId;
}

// Fetches (or kicks off measuring, see get_book_loudness_gain in
// audook_backend.py) the per-book gain and applies it - retried once after
// a delay if the backend hadn't measured it yet, rather than leaving
// normalization silently doing nothing on a book that was never analyzed.
async function applyLoudnessGainForBook(bookId: string, isRetry = false) {
  try {
    const response = await axios.get(`${getApiBase()}/books/${bookId}/loudness-gain`);
    const gainDb = response.data?.gain_db;
    if (typeof gainDb === 'number') {
      // Only apply if still on the same book and normalization is still on -
      // avoids slapping a stale/unwanted gain onto whatever's playing by
      // the time this (potentially slow, retried) measurement resolves.
      if (state.loudnessNormalizationEnabled && state.currentBook?.id === bookId) {
        await AudookPlayer.setLoudnessGain({ gainDb });
      }
    } else if (!isRetry) {
      setTimeout(() => applyLoudnessGainForBook(bookId, true), LOUDNESS_GAIN_RETRY_MS);
    }
  } catch (error) {
    console.error('Failed to fetch loudness gain:', error);
  }
}

async function cycleCompression(): Promise<string | null> {
  const currentIndex = COMPRESSION_STEPS.indexOf(state.compressionPreset);
  const nextPreset = COMPRESSION_STEPS[(currentIndex + 1) % COMPRESSION_STEPS.length];
  setState({ compressionPreset: nextPreset });
  await AudookPlayer.setCompression({ preset: nextPreset });
  return nextPreset;
}

async function toggleLoudnessNormalization(enabled: boolean) {
  setState({ loudnessNormalizationEnabled: enabled });
  if (!enabled) {
    await AudookPlayer.setLoudnessGain({ gainDb: 0 });
    return;
  }
  const book = state.currentBook;
  if (book) {
    await applyLoudnessGainForBook(book.id);
  }
}

// Convenience for call sites (HomePage/AuthorPage library grids) that only
// have a book id, not the full book+chapters payload play() needs - fetches
// it first, then resumes from the book's last saved progress like the
// desktop /api/player/play endpoint does.
async function playById(bookId: string, chapterIndex?: number, positionSeconds?: number) {
  const response = await axios.get(`${getApiBase()}/books/${bookId}`);
  const book = response.data;
  const idx = chapterIndex ?? book.progress?.chapter_index ?? 0;
  const pos = positionSeconds ?? book.progress?.position ?? 0;
  await play(book, idx, pos);
}

async function pause() {
  await AudookPlayer.pause();
  pushProgress();
}

async function resume() {
  await AudookPlayer.resume();
}

async function togglePlayPause() {
  if (state.isPlaying) {
    await pause();
  } else {
    await resume();
  }
}

async function seek(positionSeconds: number) {
  setState({ position: positionSeconds });
  await AudookPlayer.seek({ ms: positionSeconds * 1000 });
  pushProgress();
}

async function seekStep(deltaSeconds: number) {
  const newPosition = Math.max(0, Math.min(state.duration, state.position + deltaSeconds));
  await seek(newPosition);
}

async function goToNextChapter() {
  await AudookPlayer.nextChapter();
}

async function goToPreviousChapter() {
  await AudookPlayer.previousChapter();
}

async function stop() {
  await AudookPlayer.stop();
  stopProgressPushLoop();
  setState({ isPlaying: false });
}

function subscribe(listener: (s: MobilePlayerState) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getState() {
  return state;
}

export const mobilePlayerStore = {
  subscribe,
  getState,
  play,
  playById,
  pause,
  resume,
  togglePlayPause,
  seek,
  seekStep,
  setSpeed,
  fetchEqualizerPresets,
  cycleEqualizer,
  cycleCompression,
  toggleLoudnessNormalization,
  goToNextChapter,
  goToPreviousChapter,
  stop
};
