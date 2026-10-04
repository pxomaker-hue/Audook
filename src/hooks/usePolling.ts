import { useEffect, useRef } from 'react';

// setInterval that sleeps while the window/app is hidden (minimized, other
// tab, screen off) and fires once immediately on becoming visible again, so
// background polling stops costing requests/battery/NAS load for nobody.
export function usePolling(callback: () => void, intervalMs: number, enabled = true) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return;
    let timer: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timer === null) timer = setInterval(() => callbackRef.current(), intervalMs);
    };
    const stop = () => {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
    };
    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        callbackRef.current();
        start();
      }
    };

    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs, enabled]);
}
