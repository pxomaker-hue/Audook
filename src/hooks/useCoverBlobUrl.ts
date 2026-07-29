import { useEffect, useState } from 'react';
import axios from 'axios';
import { isCapacitorPlatform } from '../native/platform';
import { getApiBase } from '../config';

// On at least one real device (Xiaomi/MIUI WebView), <img src="http://...">
// to the NAS backend is blocked as mixed content even with
// android.allowMixedContent enabled and even though plain fetch()/XHR to
// the very same host succeeds. Instead of letting the <img> tag do its own
// network fetch (which the WebView polices), fetch the bytes ourselves
// over the already-working fetch path and hand the browser a same-origin
// blob: URL instead - that isn't subject to the mixed-content check at all.
export function useCoverBlobUrl(bookId: string, coverUrl: string | null | undefined): string | undefined {
  const [blobUrl, setBlobUrl] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!coverUrl || !isCapacitorPlatform || !coverUrl.startsWith('http://')) {
      setBlobUrl(undefined);
      return;
    }

    let cancelled = false;
    let objectUrl: string | undefined;
    const ownOrigin = getApiBase().replace(/\/api\/?$/, '');
    const source = coverUrl.startsWith(ownOrigin)
      ? coverUrl
      : `${getApiBase()}/books/${bookId}/cover-proxy`;

    axios
      .get(source, { responseType: 'blob' })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setBlobUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setBlobUrl(undefined);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [bookId, coverUrl]);

  if (!isCapacitorPlatform) return coverUrl ?? undefined;
  return blobUrl;
}
