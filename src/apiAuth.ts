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

// Transient failures (Wi-Fi <-> mobile data switch, VPN handshake, NAS waking
// up) must not surface as errors on the first try. Idempotent requests are
// retried a couple of times with a growing delay.
export const RETRY_MAX = 2;
export const RETRY_BASE_DELAY_MS = 600;
const RETRYABLE_STATUS = new Set([502, 503, 504]);

export function isRetryableError(error: any): boolean {
  const config = error?.config;
  if (!config || axios.isCancel(error)) return false;
  const method = String(config.method || 'get').toLowerCase();
  const idempotent = method === 'get' || method === 'head' || config.retryable === true;
  if (!idempotent) return false;
  const status = error.response?.status;
  return status === undefined ? true : RETRYABLE_STATUS.has(status);
}

export function retryDelay(attempt: number): number {
  return RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
}

export async function retryRequest(error: any): Promise<any> {
  if (!isRetryableError(error)) throw error;
  const config = error.config;
  const attempt = (config.__retryCount ?? 0) + 1;
  if (attempt > RETRY_MAX) throw error;
  config.__retryCount = attempt;
  await new Promise(resolve => setTimeout(resolve, retryDelay(attempt)));
  return axios(config);
}

export function installApiRetry(): void {
  axios.interceptors.response.use(undefined, retryRequest);
}
