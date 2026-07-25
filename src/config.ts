// Configuration centralisée pour l'application

export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_BASE || 'http://localhost:5000/api',
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
