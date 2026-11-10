// Pure state machine behind useBackendConnection (kept separate so it can be
// unit-tested without timers or fetch).

export type CheckResult = 'ok' | 'unauthorized' | 'unreachable';

export interface ConnectionState {
  online: boolean;           // the app is shown (it was reachable recently)
  authRequired: boolean;
  failures: number;          // consecutive failed checks
  firstFailureAt: number | null;
}

// A single slow/dropped check (VPN handshake, Wi-Fi <-> mobile data switch,
// phone waking up) must not tear the whole UI down: once online, tolerate this
// many consecutive failures before going offline.
export const OFFLINE_AFTER_FAILURES = 3;

export const initialConnectionState: ConnectionState = {
  online: false,
  authRequired: false,
  failures: 0,
  firstFailureAt: null,
};

export function nextConnectionState(state: ConnectionState, result: CheckResult, now: number): ConnectionState {
  if (result === 'ok') {
    return { online: true, authRequired: false, failures: 0, firstFailureAt: null };
  }
  if (result === 'unauthorized') {
    return { online: false, authRequired: true, failures: 0, firstFailureAt: null };
  }
  const failures = state.failures + 1;
  return {
    online: state.online && failures < OFFLINE_AFTER_FAILURES,
    authRequired: false,
    failures,
    firstFailureAt: state.firstFailureAt ?? now,
  };
}

// "/api" suffix only - a plain replace('/api', '/health') also hit hostnames
// such as http://my-api-nas:5000/api.
export function healthUrl(apiBase: string): string {
  return apiBase.replace(/\/api\/?$/, '') + '/health';
}
