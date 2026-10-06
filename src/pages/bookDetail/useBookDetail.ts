import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '../../config';
import { isCapacitorPlatform } from '../../native/platform';
import { mobilePlayerStore } from '../../native/mobilePlayerStore';
import { BOOKMARKS_CHANGED_EVENT } from '../../bookmarkEvents';
import { usePolling } from '../../hooks/usePolling';
import { BookDetail, BookmarkEntry } from './types';

const PLAYER_POLL_MS = 2000;
const NOISE_REDUCTION_POLL_MS = 3000;

// Everything the book page needs from the backend: the book itself, the
// live "which chapter is playing" state, and the one-shot actions (play,
// finished flag, noise reduction, bookmarks) with their busy flags.
export function useBookDetail(id: string | undefined) {
  const apiBase = getApiBase();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeChapterIndex, setActiveChapterIndex] = useState<number | null>(null);
  const [activePosition, setActivePosition] = useState(0);

  const [togglingFinished, setTogglingFinished] = useState(false);
  const [startingCleanAudio, setStartingCleanAudio] = useState(false);
  const [togglingCleanedAudio, setTogglingCleanedAudio] = useState(false);
  const [resumingBookmarkId, setResumingBookmarkId] = useState<number | null>(null);

  // Guards against a slow response for a previous book overwriting the
  // current one after the route param changes.
  const currentId = useRef(id);
  currentId.current = id;

  // Only the first load shows the full-page "Chargement..." state; refreshes
  // (after an action, or while polling noise reduction) update in place so
  // open panels and scroll position survive.
  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const response = await axios.get(`${apiBase}/books/${id}`);
      if (currentId.current === id) setBook(response.data);
    } catch (error) {
      console.error('Failed to fetch book details:', error);
    } finally {
      if (currentId.current === id) setLoading(false);
    }
  }, [apiBase, id]);

  useEffect(() => {
    setBook(null);
    setLoading(true);
    refresh();
  }, [refresh]);

  // Which chapter of this book is playing. Mobile plays through the native
  // plugin, so the backend's own player session is always empty there - read
  // the local store instead (and react to it, no polling needed).
  const refreshPlayerState = useCallback(async () => {
    if (isCapacitorPlatform) {
      const local = mobilePlayerStore.getState();
      if (local.currentBook?.id === id) {
        setActiveChapterIndex(local.currentChapterIndex);
        setActivePosition(local.position);
      } else {
        setActiveChapterIndex(null);
      }
      return;
    }
    try {
      const response = await axios.get(`${apiBase}/player/state`);
      if (currentId.current !== id) return;
      if (response.data.currentBook?.id === id) {
        setActiveChapterIndex(response.data.currentChapterIndex ?? null);
        setActivePosition(response.data.position ?? 0);
      } else {
        setActiveChapterIndex(null);
      }
    } catch (error) {
      console.error('Failed to get player state:', error);
    }
  }, [apiBase, id]);

  useEffect(() => {
    setActiveChapterIndex(null);
    refreshPlayerState();
    if (isCapacitorPlatform) {
      return mobilePlayerStore.subscribe(() => { refreshPlayerState(); });
    }
    return undefined;
  }, [refreshPlayerState]);

  usePolling(refreshPlayerState, PLAYER_POLL_MS, !isCapacitorPlatform);

  // A bookmark added from the player shows up here right away.
  useEffect(() => {
    window.addEventListener(BOOKMARKS_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(BOOKMARKS_CHANGED_EVENT, refresh);
  }, [refresh]);

  // While a noise-reduction pass runs in the background, poll for it to
  // finish so the button/status updates without a manual refresh.
  usePolling(refresh, NOISE_REDUCTION_POLL_MS, book?.noise_reduction_status === 'processing');

  // Runs an action with its busy flag, then reloads the book.
  const run = async (
    label: string,
    setBusy: (busy: boolean) => void,
    action: () => Promise<unknown>,
    reload = true
  ) => {
    try {
      setBusy(true);
      await action();
      if (reload) await refresh();
    } catch (error) {
      console.error(`Failed to ${label}:`, error);
    } finally {
      setBusy(false);
    }
  };

  const play = async (chapterIndex?: number) => {
    if (!book) return;
    try {
      if (isCapacitorPlatform) {
        await mobilePlayerStore.play(
          book,
          chapterIndex ?? book.progress.chapter_index,
          chapterIndex === undefined ? book.progress.position : 0
        );
      } else {
        await axios.post(`${apiBase}/player/play`, {
          book_id: book.id,
          ...(chapterIndex === undefined ? {} : { chapter_index: chapterIndex })
        });
      }
      // Highlight the chapter that just started right away instead of
      // waiting for the next poll.
      refreshPlayerState();
    } catch (error) {
      console.error('Failed to play:', error);
    }
  };

  const toggleFinished = () =>
    book && run('toggle finished status', setTogglingFinished, () =>
      axios.post(`${apiBase}/books/${book.id}/finished`, { finished: !book.is_finished }));

  const cleanAudio = () =>
    book && run('start noise reduction', setStartingCleanAudio, () =>
      axios.post(`${apiBase}/books/${book.id}/clean-audio`));

  const toggleUseCleanedAudio = () =>
    book && run('toggle cleaned audio', setTogglingCleanedAudio, () =>
      axios.post(`${apiBase}/books/${book.id}/use-cleaned-audio`, { enabled: !book.use_cleaned_audio }));

  const resumeBookmark = (bookmark: BookmarkEntry) =>
    run('resume bookmark', (busy) => setResumingBookmarkId(busy ? bookmark.id : null), async () => {
      if (isCapacitorPlatform && book) {
        // Mobile plays through the native player on the phone - the backend's
        // /resume would start playback on the NAS side instead.
        await mobilePlayerStore.play(book, bookmark.chapter_index, bookmark.position_seconds);
      } else {
        await axios.post(`${apiBase}/bookmarks/${bookmark.id}/resume`);
      }
    }, false);

  const renameBookmark = async (bookmark: BookmarkEntry) => {
    const name = window.prompt('Nom du marque-page (vide pour retirer le nom)', bookmark.title || '');
    if (name === null) return;
    try {
      await axios.patch(`${apiBase}/bookmarks/${bookmark.id}`, { title: name });
      await refresh();
    } catch (error) {
      console.error('Failed to rename bookmark:', error);
    }
  };

  const deleteBookmark = async (bookmarkId: number) => {
    try {
      await axios.delete(`${apiBase}/bookmarks/${bookmarkId}`);
      await refresh();
    } catch (error) {
      console.error('Failed to delete bookmark:', error);
    }
  };

  return {
    book,
    loading,
    refresh,
    activeChapterIndex,
    activePosition,
    busy: { togglingFinished, startingCleanAudio, togglingCleanedAudio, resumingBookmarkId },
    play,
    toggleFinished,
    cleanAudio,
    toggleUseCleanedAudio,
    resumeBookmark,
    renameBookmark,
    deleteBookmark
  };
}
