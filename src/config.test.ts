// Default server address: the NAS on Android (no local backend there), localhost on
// Windows (Electron starts its own backend). A saved address always wins.
type ConfigModule = typeof import('./config');

function loadConfig(isMobile: boolean, env: Record<string, string | undefined> = {}): ConfigModule {
  let mod!: ConfigModule;
  const saved = { ...process.env };
  process.env.REACT_APP_API_BASE = env.REACT_APP_API_BASE as string;
  process.env.REACT_APP_MOBILE_API_BASE = env.REACT_APP_MOBILE_API_BASE as string;
  if (env.REACT_APP_API_BASE === undefined) delete process.env.REACT_APP_API_BASE;
  if (env.REACT_APP_MOBILE_API_BASE === undefined) delete process.env.REACT_APP_MOBILE_API_BASE;
  jest.isolateModules(() => {
    jest.doMock('./native/platform', () => ({ isCapacitorPlatform: isMobile }));
    mod = require('./config');
  });
  process.env = saved;
  return mod;
}

beforeEach(() => {
  localStorage.clear();
});

describe('default API base', () => {
  it('is the NAS address on Android', () => {
    const { getApiBase, getDefaultApiBase } = loadConfig(true);
    expect(getApiBase()).toBe('http://192.168.1.200:5000/api');
    expect(getDefaultApiBase()).toBe('http://192.168.1.200:5000/api');
  });

  it('stays localhost on Windows (Electron runs its own backend)', () => {
    const { getApiBase } = loadConfig(false);
    expect(getApiBase()).toBe('http://localhost:5000/api');
  });

  it('can be overridden at build time, per platform', () => {
    expect(loadConfig(true, { REACT_APP_MOBILE_API_BASE: 'http://10.0.0.5:5000/api/' }).getApiBase())
      .toBe('http://10.0.0.5:5000/api');
    expect(loadConfig(false, { REACT_APP_API_BASE: 'http://127.0.0.1:6000/api' }).getApiBase())
      .toBe('http://127.0.0.1:6000/api');
  });

  it('does not let the desktop override leak onto Android', () => {
    expect(loadConfig(true, { REACT_APP_API_BASE: 'http://localhost:6000/api' }).getApiBase())
      .toBe('http://192.168.1.200:5000/api');
  });
});

describe('a saved address wins, and reset returns to the platform default', () => {
  it.each([true, false])('mobile=%s', (isMobile) => {
    const { getApiBase, setApiBase, resetApiBase, getDefaultApiBase } = loadConfig(isMobile);
    setApiBase('  http://192.168.1.50:5000/api/ ');
    expect(getApiBase()).toBe('http://192.168.1.50:5000/api');
    resetApiBase();
    expect(getApiBase()).toBe(getDefaultApiBase());
  });
});
