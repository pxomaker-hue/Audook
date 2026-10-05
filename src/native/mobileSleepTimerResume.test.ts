// The native countdown runs in Kotlin and tells the WebView about it with
// 'sleepTimerUpdate' events. With the screen off the WebView is suspended and the
// final "timer over" event (remainingSeconds: null) is LOST - the book stops, but
// the JS side kept a stale number: the sleep button stayed "active" and the next
// click continued the cycle (10 -> 15 min) instead of restarting at 5.
// The store must notice the expiry by itself when the app is visible again.
import { renderHook, act } from '@testing-library/react';

type Handler = (data: any) => void;
const handlers: Record<string, Handler> = {};
const mockNative: Record<string, jest.Mock> = {};

jest.mock('./AudookPlayer', () => ({
  __esModule: true,
  default: new Proxy({}, {
    get: (_target, name: string) => {
      if (name === 'addListener') {
        return (event: string, handler: Handler) => {
          handlers[event] = handler;
          return Promise.resolve({ remove: () => {} });
        };
      }
      if (!mockNative[name]) mockNative[name] = jest.fn(() => Promise.resolve());
      return mockNative[name];
    }
  })
}));
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() }
}));
jest.mock('../config', () => ({ getApiBase: () => 'http://nas/api', withApiToken: (u: string) => u }));

import axios from 'axios';
import { mobilePlayerStore } from './mobilePlayerStore';
import { usePlayerState } from '../hooks/useMobilePlayerState';

const book = { id: 'b1', title: 'Book', chapters: [{ title: 'c1', audio_file: '/a.mp3', duration: 3600 }] };

const setHidden = (hidden: boolean) => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
  act(() => { document.dispatchEvent(new Event('visibilitychange')); });
};

beforeEach(() => {
  jest.useFakeTimers('modern');
  (axios.get as jest.Mock).mockResolvedValue({ data: [] });
  Object.values(mockNative).forEach((fn) => fn.mockClear());
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
});

afterEach(async () => {
  await mobilePlayerStore.setSleepTimer(null);
  jest.useRealTimers();
});

const minutesSent = () => mockNative.setSleepTimer.mock.calls.slice(-1)[0][0].minutes;

it('detects the expiry on return when the native "timer over" event was lost', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => { await mobilePlayerStore.play(book); }); // registers the native listeners

  const click = () => act(async () => { await result.current.handleCycleSleepTimer(); });
  await click(); // 5 min
  await click(); // 10 min
  expect(minutesSent()).toBe(10);
  expect(result.current.state.sleepTimerRemainingSeconds).toBe(600);

  // screen off: 11 minutes pass, the WebView runs nothing and never receives the final null event
  setHidden(true);
  jest.setSystemTime(Date.now() + 11 * 60 * 1000);
  setHidden(false); // user comes back

  expect(result.current.state.sleepTimerRemainingSeconds).toBeNull();
  await click();
  expect(minutesSent()).toBe(5); // starts over, not 15
});

it('keeps a still-running timer when the app comes back early', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => { await mobilePlayerStore.play(book); });
  await act(async () => { await result.current.handleCycleSleepTimer(); }); // 5 min
  act(() => handlers.sleepTimerUpdate({ remainingSeconds: 250 }));

  setHidden(true);
  jest.setSystemTime(Date.now() + 60 * 1000); // only 1 minute away
  setHidden(false);

  expect(result.current.state.sleepTimerRemainingSeconds).toBe(250); // untouched, still running
  await act(async () => { await result.current.handleCycleSleepTimer(); });
  expect(minutesSent()).toBe(10);
});

it('also expires on its own while the app stays in the foreground', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => { await mobilePlayerStore.play(book); });
  await act(async () => { await result.current.handleCycleSleepTimer(); }); // 5 min
  expect(result.current.state.sleepTimerRemainingSeconds).toBe(300);

  await act(async () => { jest.advanceTimersByTime(5 * 60 * 1000 + 2000); }); // no native event at all
  expect(result.current.state.sleepTimerRemainingSeconds).toBeNull();
});
