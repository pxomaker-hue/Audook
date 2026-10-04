import axios from 'axios';
import { getApiBase, getApiToken } from './config';

// Attaches the optional API token (see config.ts getApiToken) to a request
// aimed at the Audook backend. Requests to any other host (cover images from
// a Plex server, online metadata...) never receive it.
export function attachApiToken<T extends { url?: string; headers: { set: (name: string, value: string) => unknown } }>(config: T): T {
  const token = getApiToken();
  if (token && typeof config.url === 'string' && config.url.startsWith(getApiBase())) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
}

export function installApiAuth(): void {
  axios.interceptors.request.use(attachApiToken);
}
