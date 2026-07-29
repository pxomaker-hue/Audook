import React from 'react';
import { useCoverBlobUrl } from '../hooks/useCoverBlobUrl';

interface CoverImageProps {
  bookId: string;
  coverUrl: string | null | undefined;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  fallback?: React.ReactNode;
}

// Drop-in replacement for <img src={cover_url} /> - see useCoverBlobUrl for
// why mobile can't just use the URL directly.
const CoverImage: React.FC<CoverImageProps> = ({ bookId, coverUrl, alt, className, style, fallback }) => {
  const src = useCoverBlobUrl(bookId, coverUrl);
  if (!src) return fallback !== undefined ? <>{fallback}</> : null;
  return <img src={src} alt={alt} className={className} style={style} />;
};

export default CoverImage;
