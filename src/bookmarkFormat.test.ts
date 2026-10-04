import { formatBookmarkDate, formatBookmarkPosition } from './bookmarkFormat';

describe('formatBookmarkPosition', () => {
  it('shows minutes:seconds under an hour', () => {
    expect(formatBookmarkPosition(0)).toBe('0:00');
    expect(formatBookmarkPosition(65.9)).toBe('1:05');
    expect(formatBookmarkPosition(3599)).toBe('59:59');
  });

  it('adds hours when needed', () => {
    expect(formatBookmarkPosition(3600)).toBe('1:00:00');
    expect(formatBookmarkPosition(4503)).toBe('1:15:03');
  });

  it('is safe on bad input', () => {
    expect(formatBookmarkPosition(-5)).toBe('0:00');
    expect(formatBookmarkPosition(NaN)).toBe('0:00');
  });
});

describe('formatBookmarkDate', () => {
  it('returns an empty string for missing or invalid dates', () => {
    expect(formatBookmarkDate(null)).toBe('');
    expect(formatBookmarkDate(undefined)).toBe('');
    expect(formatBookmarkDate('not a date')).toBe('');
  });

  it('treats a timezone-less backend timestamp as UTC', () => {
    expect(formatBookmarkDate('2026-10-04T19:40:00')).toBe(formatBookmarkDate('2026-10-04T19:40:00Z'));
  });

  it('formats day, month and time in French', () => {
    expect(formatBookmarkDate('2026-10-04T12:00:00Z')).toMatch(/4 oct\./);
  });
});
