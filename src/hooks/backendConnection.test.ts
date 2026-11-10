import { healthUrl, initialConnectionState, nextConnectionState, OFFLINE_AFTER_FAILURES } from './backendConnection';

describe('nextConnectionState', () => {
  const online = nextConnectionState(initialConnectionState, 'ok', 0);

  it('goes online on the first success', () => {
    expect(online).toEqual({ online: true, authRequired: false, failures: 0, firstFailureAt: null });
  });

  it('stays online through isolated failures (VPN hiccup)', () => {
    let s = online;
    for (let i = 0; i < OFFLINE_AFTER_FAILURES - 1; i++) s = nextConnectionState(s, 'unreachable', 100 + i);
    expect(s.online).toBe(true);
    expect(s.failures).toBe(OFFLINE_AFTER_FAILURES - 1);
  });

  it('goes offline after consecutive failures and recovers on success', () => {
    let s = online;
    for (let i = 0; i < OFFLINE_AFTER_FAILURES; i++) s = nextConnectionState(s, 'unreachable', 100 + i);
    expect(s.online).toBe(false);
    expect(s.firstFailureAt).toBe(100);
    expect(nextConnectionState(s, 'ok', 200).online).toBe(true);
  });

  it('a success resets the failure streak', () => {
    let s = nextConnectionState(online, 'unreachable', 1);
    s = nextConnectionState(s, 'ok', 2);
    expect(s.failures).toBe(0);
  });

  it('unauthorized goes offline immediately with authRequired', () => {
    const s = nextConnectionState(online, 'unauthorized', 5);
    expect(s).toMatchObject({ online: false, authRequired: true });
  });
});

describe('healthUrl', () => {
  it('only strips the trailing /api', () => {
    expect(healthUrl('http://my-api-nas:5000/api')).toBe('http://my-api-nas:5000/health');
    expect(healthUrl('http://10.0.0.2:5000/api/')).toBe('http://10.0.0.2:5000/health');
  });
});
