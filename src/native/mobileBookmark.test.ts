// Mobile "add bookmark": the backend reads `position`, and the book page must
// be told to refresh. (The app used to send `position_seconds`, which the
// backend ignored - so no bookmark was ever saved from the phone.)
import { renderHook, act } from '@testing-library/react';

jest.mock('./AudookPlayer', () => ({
  __esModule: true,
  default: new Proxy({}, { get: () => () => Promise.resolve({ remove: () => {} }) })
}));
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() }
}));
jest.mock('../config', () => ({ getApiBase: () => 'http://nas/api', withApiToken: (u: string) => u }));

import axios from 'axios';
import { mobilePlayerStore } from './mobilePlayerStore';
import { usePlayerState } from '../hooks/useMobilePlayerState';
import { BOOKMARKS_CHANGED_EVENT } from '../bookmarkEvents';

const book = { id: 'b1', title: 'Book', chapters: [{ title: 'c1', audio_file: '/a.mp3', duration: 600 }] };

beforeEach(() => {
  (axios.get as jest.Mock).mockResolvedValue({ data: [] });
  (axios.post as jest.Mock).mockResolvedValue({ data: {} });
});

it('posts chapter_index + position and notifies the book page', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => {
    await mobilePlayerStore.play(book, 0, 123);
  });
  const changed = jest.fn();
  window.addEventListener(BOOKMARKS_CHANGED_EVENT, changed);

  await act(async () => {
    await result.current.handleAddBookmark();
  });
  window.removeEventListener(BOOKMARKS_CHANGED_EVENT, changed);

  const call = (axios.post as jest.Mock).mock.calls.find(([url]) => String(url).endsWith('/books/b1/bookmarks'));
  expect(call).toBeDefined();
  expect(call![1]).toEqual({ chapter_index: 0, position: 123 });
  expect(changed).toHaveBeenCalledTimes(1);
});
