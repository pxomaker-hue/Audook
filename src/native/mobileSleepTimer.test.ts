// Sleep timer wiring on mobile: UI cycle -> store -> native plugin, and
// native 'sleepTimerUpdate' events -> state. The countdown itself runs in
// Kotlin (AudookPlayerPlugin.kt) so it survives backgrounding.
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
  default: { get: jest.fn(() => Promise.resolve({ data: [] })), post: jest.fn(() => Promise.resolve({ data: {} })) }
}));
jest.mock('../config', () => ({ getApiBase: () => 'http://nas/api', withApiToken: (url: string) => url }));

import axios from 'axios';
import { mobilePlayerStore } from './mobilePlayerStore';
import { usePlayerState } from '../hooks/useMobilePlayerState';

const book = {
  id: 'b1',
  title: 'Book',
  chapters: [{ title: 'c1', audio_file: '/a.mp3', duration: 60 }]
};

beforeEach(() => {
  // CRA's jest config uses resetMocks: true, which wipes mock implementations
  // before every test - re-arm the ones the code under test relies on.
  (axios.get as jest.Mock).mockResolvedValue({ data: [] });
  Object.values(mockNative).forEach((fn) => fn.mockClear());
});

describe('mobilePlayerStore sleep timer', () => {
  it('forwards minutes to the native plugin and shows the full duration immediately', async () => {
    await mobilePlayerStore.play(book); // registers the native listeners
    await mobilePlayerStore.setSleepTimer(10);
    expect(mockNative.setSleepTimer).toHaveBeenCalledWith({ minutes: 10 });
    expect(mobilePlayerStore.getState().sleepTimerRemainingSeconds).toBe(600);
  });

  it('turns the timer off with null', async () => {
    await mobilePlayerStore.setSleepTimer(5);
    await mobilePlayerStore.setSleepTimer(null);
    expect(mockNative.setSleepTimer).toHaveBeenLastCalledWith({ minutes: null });
    expect(mobilePlayerStore.getState().sleepTimerRemainingSeconds).toBeNull();
  });

  it('follows the countdown pushed by the native side, including expiry', async () => {
    await mobilePlayerStore.play(book);
    act(() => handlers.sleepTimerUpdate({ remainingSeconds: 42 }));
    expect(mobilePlayerStore.getState().sleepTimerRemainingSeconds).toBe(42);
    act(() => handlers.sleepTimerUpdate({ remainingSeconds: null }));
    expect(mobilePlayerStore.getState().sleepTimerRemainingSeconds).toBeNull();
  });
});

describe('useMobilePlayerState.handleCycleSleepTimer', () => {
  it('cycles off -> 5 -> 10 -> 15 -> 20 -> 30 -> 60 -> off', async () => {
    const { result } = renderHook(() => usePlayerState());
    const sent: Array<number | null> = [];
    for (let i = 0; i < 7; i++) {
      await act(async () => {
        await result.current.handleCycleSleepTimer();
      });
      sent.push(mockNative.setSleepTimer.mock.calls[i][0].minutes);
    }
    expect(sent).toEqual([5, 10, 15, 20, 30, 60, null]);
  });
});

describe('sleep timer button after the timer ends', () => {
  it('starts over at 5 minutes instead of continuing from the last setting', async () => {
    const { result } = renderHook(() => usePlayerState());
    await mobilePlayerStore.play(book); // registers the native listeners
    mockNative.setSleepTimer?.mockClear();
    const click = () => act(async () => { await result.current.handleCycleSleepTimer(); });
    const lastMinutes = () => mockNative.setSleepTimer.mock.calls.slice(-1)[0][0].minutes;

    await click(); // 5
    await click(); // 10
    expect(lastMinutes()).toBe(10);

    act(() => handlers.sleepTimerUpdate({ remainingSeconds: 30 })); // counting down
    act(() => handlers.sleepTimerUpdate({ remainingSeconds: null })); // 10 min elapsed
    await click();
    expect(lastMinutes()).toBe(5);
  });

  it('keeps cycling normally while the timer is still running', async () => {
    const { result } = renderHook(() => usePlayerState());
    await mobilePlayerStore.play(book);
    mockNative.setSleepTimer?.mockClear();
    const click = () => act(async () => { await result.current.handleCycleSleepTimer(); });
    await click(); // 5 (store sets remaining = 300 right away)
    act(() => handlers.sleepTimerUpdate({ remainingSeconds: 250 }));
    await click();
    expect(mockNative.setSleepTimer.mock.calls.slice(-1)[0][0].minutes).toBe(10);
  });
});
