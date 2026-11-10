import { getApiBase, authHeaders } from './config';
import { isCapacitorPlatform } from './native/platform';
import AudookPlayer from './native/AudookPlayer';

export const APP_VERSION = process.env.REACT_APP_VERSION || '';

export interface UpdateInfo {
  current: string;
  latest: string;
  available: boolean;
  notes: string;
  selfUpdate: boolean;
  asset: { file: string; url: string; sha256: string; size: number } | null;
}

// Android asks the backend (the NAS) for the signed manifest, comparing against its own version.
export async function checkForUpdate(): Promise<UpdateInfo> {
  const platform = isCapacitorPlatform ? 'android' : 'windows';
  const query = isCapacitorPlatform && APP_VERSION ? `&current=${encodeURIComponent(APP_VERSION)}` : '';
  const response = await fetch(`${getApiBase()}/update/check?platform=${platform}${query}`, { headers: authHeaders() });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data as UpdateInfo;
}

// Windows: the backend downloads, verifies (SHA-256 from the signed manifest) and launches the
// installer, then the app quits so the installer can replace it. Android: the native plugin
// downloads, verifies the SHA-256 and opens the system installer.
export async function installUpdate(info: UpdateInfo): Promise<void> {
  if (isCapacitorPlatform) {
    if (!info.asset) throw new Error('Aucun fichier à installer');
    await AudookPlayer.installUpdate({ url: info.asset.url, sha256: info.asset.sha256, size: info.asset.size });
    return;
  }
  const response = await fetch(`${getApiBase()}/update/install`, { method: 'POST', headers: authHeaders() });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  window.electron?.quitForUpdate();
}
