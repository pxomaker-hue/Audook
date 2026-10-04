// Configuration centralisée pour l'application

const STORAGE_KEY = 'audook_api_base';
const DEFAULT_BASE_URL = process.env.REACT_APP_API_BASE || 'http://localhost:5000/api';

function normalizeBase(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

// L'URL du backend est modifiable à l'exécution (localStorage) sans
// rebuild - indispensable pour l'app mobile qui doit pointer vers l'IP
// LAN du NAS de l'utilisateur. Retombe sur la variable d'env de build
// (comportement Electron inchangé) si rien n'est enregistré.
export function getApiBase(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return normalizeBase(stored);
  } catch {
    // localStorage indisponible (SSR, contexte restreint) - ignorer
  }
  return normalizeBase(DEFAULT_BASE_URL);
}

export function setApiBase(url: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, normalizeBase(url));
  } catch {
    // ignorer si localStorage indisponible
  }
}

export function resetApiBase(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignorer
  }
}

const TOKEN_STORAGE_KEY = 'audook_api_token';

// Jeton d'accès optionnel : seulement nécessaire si le backend (typiquement
// sur le NAS) a été lancé avec AUDOOK_API_TOKEN. Vide = pas d'authentification.
export function getApiToken(): string {
  try {
    return (localStorage.getItem(TOKEN_STORAGE_KEY) || '').trim();
  } catch {
    return '';
  }
}

export function setApiToken(token: string): void {
  try {
    const trimmed = token.trim();
    if (trimmed) localStorage.setItem(TOKEN_STORAGE_KEY, trimmed);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // ignorer si localStorage indisponible
  }
}

// En-têtes d'authentification pour les requêtes fetch() maison (axios les
// reçoit via l'intercepteur de apiAuth.ts).
export function authHeaders(): Record<string, string> {
  const token = getApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Pour les URLs lues par quelqu'un qui ne peut pas envoyer d'en-têtes
// (ExoPlayer, Chromecast) : le jeton passe dans la query string. Le backend
// ne l'accepte ainsi que sur /api/cast/local-audio.
export function withApiToken(url: string): string {
  const token = getApiToken();
  if (!token) return url;
  return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}

export const API_CONFIG = {
  get BASE_URL(): string {
    return getApiBase();
  },
  HEALTH_CHECK_INTERVAL: 5000, // Vérifier la connexion toutes les 5 secondes
  REQUEST_TIMEOUT: 10000, // Timeout pour les requêtes HTTP
  RETRY_ATTEMPTS: 3, // Nombre de tentatives avant erreur
  RETRY_DELAY: 1000, // Délai entre les tentatives (ms)
};

// Types pour l'API
export interface ApiError {
  message: string;
  code?: string;
  statusCode?: number;
}

// Utilitaire pour les requêtes avec retry
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
  retries = API_CONFIG.RETRY_ATTEMPTS
): Promise<T> {
  const url = `${API_CONFIG.BASE_URL}${endpoint}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.REQUEST_TIMEOUT);

    const response = await fetch(url, {
      ...options,
      headers: { ...authHeaders(), ...(options?.headers as Record<string, string> | undefined) },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (retries > 0 && error instanceof TypeError) {
      // Retry on network errors
      await new Promise(resolve => setTimeout(resolve, API_CONFIG.RETRY_DELAY));
      return apiFetch<T>(endpoint, options, retries - 1);
    }
    throw error;
  }
}
