export type ThemePreference = 'light' | 'dark' | 'auto';

const STORAGE_KEY = 'theme';
const media = window.matchMedia?.('(prefers-color-scheme: dark)');

export function getThemePreference(): ThemePreference {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark' || saved === 'auto') return saved;
  } catch {
    // storage unavailable (private mode etc.) - fall through to default
  }
  return 'auto';
}

function resolve(pref: ThemePreference): 'light' | 'dark' {
  if (pref === 'auto') return media?.matches ? 'dark' : 'light';
  return pref;
}

// Sets data-theme on <html>; App.css only needs a :root[data-theme="dark"]
// override block, "auto" is resolved here and kept in sync with the OS.
export function applyTheme(pref: ThemePreference = getThemePreference()) {
  document.documentElement.dataset.theme = resolve(pref);
}

export function setThemePreference(pref: ThemePreference) {
  try {
    localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    // non-fatal: the choice just won't persist
  }
  applyTheme(pref);
}

media?.addEventListener?.('change', () => {
  if (getThemePreference() === 'auto') applyTheme('auto');
});
