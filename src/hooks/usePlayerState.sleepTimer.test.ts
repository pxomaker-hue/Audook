// Desktop sleep timer vs. the 1 s state polling: a poll that STARTED before the
// click but is answered AFTER the click's own response carries the old "no
// timer" state. It must not overwrite the fresh state - otherwise the timer
// shows as off and the step index resets, so the next click restarts at 5 min.
import { renderHook, act } from '@testing-library/react';

jest.mock('axios', () => ({ __esModule: true, default: { get: jest.fn(), post: jest.fn() } }));
jest.mock('./usePolling', () => ({ usePolling: jest.fn() }));
jest.mock('../config', () => ({ getApiBase: () => 'http://localhost:5000/api' }));
jest.mock('../bookmarkEvents', () => ({ notifyBookmarksChanged: jest.fn() }));

import axios from 'axios';
import { usePlayerState } from './usePlayerState';
import { usePolling } from './usePolling';

const idle = { data: { is_playing: false, sleep_timer_remaining_seconds: null } };

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}

let stateQueue: Array<Promise<any>>;

beforeEach(() => {
  stateQueue = [];
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (url.includes('/equalizer/presets')) return Promise.resolve({ data: [] });
    if (url.includes('/player/state')) return stateQueue.shift() ?? Promise.resolve(idle);
    return Promise.resolve({ data: {} });
  });
  (axios.post as jest.Mock).mockReset();
});

// usePolling is mocked: grab the poll callback the hook registered and fire it by hand.
const firePoll = async () => {
  const calls = (usePolling as jest.Mock).mock.calls;
  await act(async () => { calls[calls.length - 1][0](); });
};

it('ignores a stale poll answered after the click response, and keeps cycling 5 -> 10', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => {}); // initial fetch

  const post = deferred<any>();
  (axios.post as jest.Mock).mockReturnValueOnce(post.promise);
  let click!: Promise<void>;
  await act(async () => { click = result.current.handleCycleSleepTimer(); }); // POST in flight (5 min)

  const stalePoll = deferred<any>();
  stateQueue.push(stalePoll.promise);
  await firePoll(); // poll started now, before the POST has been answered

  await act(async () => { post.resolve({ data: { sleep_timer_remaining_seconds: 300 } }); await click; });
  expect(result.current.state.sleepTimerRemainingSeconds).toBe(300);

  await act(async () => { stalePoll.resolve(idle); }); // old "no timer" state arrives late
  expect(result.current.state.sleepTimerRemainingSeconds).toBe(300); // not overwritten

  (axios.post as jest.Mock).mockResolvedValueOnce({ data: { sleep_timer_remaining_seconds: 600 } });
  await act(async () => { await result.current.handleCycleSleepTimer(); });
  expect((axios.post as jest.Mock).mock.calls.slice(-1)[0][1]).toEqual({ minutes: 10 }); // not 5 again
});

it('still follows the real expiry reported by a later poll', async () => {
  const { result } = renderHook(() => usePlayerState());
  await act(async () => {});
  (axios.post as jest.Mock).mockResolvedValueOnce({ data: { sleep_timer_remaining_seconds: 300 } });
  await act(async () => { await result.current.handleCycleSleepTimer(); });
  expect(result.current.state.sleepTimerRemainingSeconds).toBe(300);

  stateQueue.push(Promise.resolve(idle)); // the timer ended on the backend
  await firePoll();
  expect(result.current.state.sleepTimerRemainingSeconds).toBeNull();
});
