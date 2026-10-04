// Optional API token: storage helpers, axios header injection, media URLs.
jest.mock('axios', () => ({
  __esModule: true,
  default: { interceptors: { request: { use: jest.fn() } } }
}));

import axios from 'axios';
import { attachApiToken, installApiAuth } from './apiAuth';
import { authHeaders, getApiBase, getApiToken, setApiToken, withApiToken } from './config';

const fakeConfig = (url: string) => {
  const set = jest.fn();
  return { config: { url, headers: { set } }, set };
};

beforeEach(() => {
  localStorage.clear();
});

describe('token storage', () => {
  it('is empty by default and trims what is saved', () => {
    expect(getApiToken()).toBe('');
    setApiToken('  abc123  ');
    expect(getApiToken()).toBe('abc123');
  });

  it('saving an empty token removes it', () => {
    setApiToken('abc');
    setApiToken('   ');
    expect(getApiToken()).toBe('');
    expect(localStorage.getItem('audook_api_token')).toBeNull();
  });
});

describe('attachApiToken (axios interceptor logic)', () => {
  it('adds the Bearer header to requests aimed at the backend', () => {
    setApiToken('abc');
    const { config, set } = fakeConfig(`${getApiBase()}/books`);
    attachApiToken(config);
    expect(set).toHaveBeenCalledWith('Authorization', 'Bearer abc');
  });

  it('never sends the token to another host', () => {
    setApiToken('abc');
    const { config, set } = fakeConfig('https://plex.example.com/library/covers/1.jpg');
    attachApiToken(config);
    expect(set).not.toHaveBeenCalled();
  });

  it('adds nothing when no token is configured', () => {
    const { config, set } = fakeConfig(`${getApiBase()}/books`);
    attachApiToken(config);
    expect(set).not.toHaveBeenCalled();
  });

  it('is registered on axios by installApiAuth', () => {
    installApiAuth();
    expect(axios.interceptors.request.use).toHaveBeenCalledWith(attachApiToken);
  });
});

describe('authHeaders / withApiToken', () => {
  it('authHeaders is empty without a token and a Bearer header with one', () => {
    expect(authHeaders()).toEqual({});
    setApiToken('abc');
    expect(authHeaders()).toEqual({ Authorization: 'Bearer abc' });
  });

  it('withApiToken leaves URLs alone without a token', () => {
    expect(withApiToken('http://nas/api/cast/local-audio?path=a')).toBe('http://nas/api/cast/local-audio?path=a');
  });

  it('withApiToken appends the token with the right separator and encoding', () => {
    setApiToken('a b&c');
    expect(withApiToken('http://nas/api/x?path=a')).toBe('http://nas/api/x?path=a&token=a%20b%26c');
    expect(withApiToken('http://nas/api/x')).toBe('http://nas/api/x?token=a%20b%26c');
  });
});
