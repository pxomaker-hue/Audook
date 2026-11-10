import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface AuthorPhotoProps {
  src: string;
  alt: string;
  style?: React.CSSProperties;
}

const PROXY_MARKER = '/author-photo-proxy';

// <img> for an author photo. When the backend hides the source server's token
// behind its own proxy URL, fetch it through axios (so the API token header
// is sent and the WebView doesn't hit mixed-content limits); other URLs are
// used directly.
const AuthorPhoto: React.FC<AuthorPhotoProps> = ({ src, alt, style }) => {
  const proxied = src.includes(PROXY_MARKER);
  const [blobUrl, setBlobUrl] = useState<string | undefined>();

  useEffect(() => {
    if (!proxied) return;
    let cancelled = false;
    let objectUrl: string | undefined;
    axios
      .get(src, { responseType: 'blob' })
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
  }, [src, proxied]);

  const resolved = proxied ? blobUrl : src;
  return resolved ? <img src={resolved} alt={alt} style={style} /> : null;
};

export default AuthorPhoto;
