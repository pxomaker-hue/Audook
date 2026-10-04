// ExoPlayer (and a Chromecast, which loads the same URLs) cannot send an
// Authorization header, so the playlist URLs must carry the API token.
const mockPlay = jest.fn();

jest.mock('./AudookPlayer', () => ({
  __esModule: true,
  default: new Proxy({}, {
    get: (_t, name: string) => (name === 'play' ? mockPlay : () => Promise.resolve({ remove: () => {} }))
  })
}));
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn(() => Promise.resolve({ data: [] })), post: jest.fn(() => Promise.resolve({ data: {} })) }
}));

import { mobilePlayerStore } from './mobilePlayerStore';
import { setApiBase, setApiToken } from '../config';

const book = { id: 'b1', title: 'Book', chapters: [{ title: 'c1', audio_file: '/books/a b.m4b', duration: 60 }] };

beforeEach(() => {
  localStorage.clear();
  setApiBase('http://nas:5000/api');
  mockPlay.mockResolvedValue(undefined);
});

it('adds the token to the playlist URLs when one is configured', async () => {
  setApiToken('tok en');
  await mobilePlayerStore.play(book);
  const { chapters } = mockPlay.mock.calls[0][0];
  expect(chapters[0].url).toBe('http://nas:5000/api/cast/local-audio?path=%2Fbooks%2Fa%20b.m4b&token=tok%20en');
});

it('leaves the URLs untouched without a token', async () => {
  await mobilePlayerStore.play(book);
  const { chapters } = mockPlay.mock.calls[0][0];
  expect(chapters[0].url).toBe('http://nas:5000/api/cast/local-audio?path=%2Fbooks%2Fa%20b.m4b');
});
