import { renderHook } from '@testing-library/react';
import { usePolling } from './usePolling';

const setHidden = (hidden: boolean) => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
  document.dispatchEvent(new Event('visibilitychange'));
};

describe('usePolling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('calls the callback on every interval tick', () => {
    const callback = jest.fn();
    renderHook(() => usePolling(callback, 1000));
    jest.advanceTimersByTime(3500);
    expect(callback).toHaveBeenCalledTimes(3);
  });

  it('does nothing while disabled, and starts once enabled', () => {
    const callback = jest.fn();
    const { rerender } = renderHook(({ enabled }) => usePolling(callback, 1000, enabled), {
      initialProps: { enabled: false }
    });
    jest.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
    rerender({ enabled: true });
    jest.advanceTimersByTime(2000);
    expect(callback).toHaveBeenCalledTimes(2);
  });

  it('pauses while the page is hidden and fires immediately when it is visible again', () => {
    const callback = jest.fn();
    renderHook(() => usePolling(callback, 1000));
    jest.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(1);

    setHidden(true);
    jest.advanceTimersByTime(10000);
    expect(callback).toHaveBeenCalledTimes(1); // nothing while hidden

    setHidden(false);
    expect(callback).toHaveBeenCalledTimes(2); // immediate refresh on return
    jest.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(3); // and the interval resumes
  });

  it('does not start polling when mounted while hidden', () => {
    setHidden(true);
    const callback = jest.fn();
    renderHook(() => usePolling(callback, 1000));
    jest.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
  });

  it('always calls the latest callback without restarting the timer', () => {
    const first = jest.fn();
    const second = jest.fn();
    const { rerender } = renderHook(({ cb }) => usePolling(cb, 1000), { initialProps: { cb: first } });
    jest.advanceTimersByTime(1000);
    rerender({ cb: second });
    jest.advanceTimersByTime(1000);
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it('stops polling and removes its listener on unmount', () => {
    const callback = jest.fn();
    const { unmount } = renderHook(() => usePolling(callback, 1000));
    unmount();
    jest.advanceTimersByTime(5000);
    setHidden(false);
    expect(callback).not.toHaveBeenCalled();
  });
});
