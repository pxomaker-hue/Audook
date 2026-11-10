import { useEffect, useRef, useState } from 'react';
import { authHeaders, getApiBase } from '../config';
import { CheckResult, ConnectionState, healthUrl, initialConnectionState, nextConnectionState } from './backendConnection';

const CHECK_TIMEOUT_MS = 10000;         // slow VPN links need more than 5 s
const FAST_INTERVAL_MS = 1500;          // while not (yet) online: backend may be starting
const ONLINE_INTERVAL_MS = 10000;       // once online: light heartbeat

async function runCheck(): Promise<CheckResult> {
  const apiBase = getApiBase();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), CHECK_TIMEOUT_MS);
  try {
    const live = await fetch(healthUrl(apiBase), { signal: controller.signal });
    if (!live.ok) return 'unreachable';
    // /health is public (liveness); /api/health needs the API token when the
    // backend has one - tells "unreachable" apart from "token missing/wrong".
    const auth = await fetch(`${apiBase}/health`, { headers: authHeaders(), signal: controller.signal });
    if (auth.status === 401) return 'unauthorized';
    return 'ok';
  } catch {
    return 'unreachable';
  } finally {
    clearTimeout(timeout);
  }
}

// Tracks backend reachability without flapping: checks never overlap, a
// single failure doesn't unmount the UI once connected, and a check is fired
// right away when the app comes back to the foreground / the network returns.
export function useBackendConnection(errorThresholdMs: number) {
  const [state, setState] = useState<ConnectionState>(initialConnectionState);
  const stateRef = useRef(state);
  stateRef.current = state;
  const [, forceTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const schedule = () => {
      if (cancelled) return;
      const delay = stateRef.current.online ? ONLINE_INTERVAL_MS : FAST_INTERVAL_MS;
      timer = setTimeout(check, delay);
    };

    const check = async () => {
      if (cancelled || inFlight) return;
      if (timer) clearTimeout(timer);
      inFlight = true;
      const result = await runCheck();
      inFlight = false;
      if (cancelled) return;
      const next = nextConnectionState(stateRef.current, result, Date.now());
      stateRef.current = next;
      setState(next);
      forceTick(t => t + 1);
      schedule();
    };

    const wake = () => { if (!document.hidden) check(); };
    document.addEventListener('visibilitychange', wake);
    window.addEventListener('online', wake);

    check();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', wake);
      window.removeEventListener('online', wake);
    };
  }, []);

  const showError = !state.online && (
    state.authRequired ||
    (state.firstFailureAt !== null && Date.now() - state.firstFailureAt >= errorThresholdMs)
  );
  return {
    backendOnline: state.online,
    authRequired: state.authRequired,
    showError,
    // Online but the last checks failed: show a discreet hint, keep the UI.
    reconnecting: state.online && state.failures > 0,
    resetFailures: () => setState(s => ({ ...s, firstFailureAt: null })),
  };
}
