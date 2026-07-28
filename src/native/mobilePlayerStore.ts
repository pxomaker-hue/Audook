import axios from 'axios';
import AudookPlayer from './AudookPlayer';
import { getApiBase } from '../config';

// Singleton playback state for the mobile (Capacitor) player, independent of
// React's component tree - HomePage/BookDetailPage/AuthorPage all need to
// trigger playback on the same native player instance regardless of which
// component is currently mounted, and useMobilePlayerState (the hook
// components read from) just subscribes to this store.

export interface MobilePlayerState {
  isPlaying: boolean;
  currentBook: any | null;
  currentChapterIndex: number;
  position: number; // seconds
  duration: number; // seconds
}

const PROGRESS_PUSH_INTERVAL_MS = 15000;

let state: MobilePlayerState = {
  isPlaying: false,
  currentBook: null,
  currentChapterIndex: 0,
  position: 0,
  duration: 0
};

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
  AudookPlayer.addListener('ended', () => {
    goToNextChapter();
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

async function playChapter(book: any, chapterIndex: number, positionSeconds = 0) {
  ensureNativeListeners();
  const chapter = book.chapters?.[chapterIndex];
  if (!chapter) return;

  const url = `${getApiBase()}/cast/local-audio?path=${encodeURIComponent(chapter.audio_file)}`;
  setState({ currentBook: book, currentChapterIndex: chapterIndex, position: positionSeconds, duration: chapter.duration || 0 });

  await AudookPlayer.play({ url, title: chapter.title || book.title, cover: book.cover_url || undefined });
  if (positionSeconds > 0) {
    await AudookPlayer.seek({ ms: positionSeconds * 1000 });
  }
  startProgressPushLoop();
}

async function play(book: any, chapterIndex?: number, positionSeconds?: number) {
  const idx = chapterIndex ?? 0;
  const pos = positionSeconds ?? 0;
  await playChapter(book, idx, pos);
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
  const book = state.currentBook;
  if (!book || !book.chapters) return;
  pushProgress(true);
  const nextIndex = state.currentChapterIndex + 1;
  if (nextIndex >= book.chapters.length) {
    await AudookPlayer.stop();
    stopProgressPushLoop();
    return;
  }
  await playChapter(book, nextIndex, 0);
}

async function goToPreviousChapter() {
  const book = state.currentBook;
  if (!book) return;
  const prevIndex = Math.max(0, state.currentChapterIndex - 1);
  await playChapter(book, prevIndex, 0);
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
  goToNextChapter,
  goToPreviousChapter,
  stop
};
