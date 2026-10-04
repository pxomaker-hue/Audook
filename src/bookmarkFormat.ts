// "75:03" / "1:15:03" - hours only when needed.
export function formatBookmarkPosition(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const seconds = safe % 60;
  const ss = seconds.toString().padStart(2, '0');
  return hours > 0 ? `${hours}:${minutes.toString().padStart(2, '0')}:${ss}` : `${minutes}:${ss}`;
}

// The backend stores UTC timestamps without a timezone suffix
// ("2026-10-04T19:40:00") - read them as UTC, show them in local time.
export function formatBookmarkDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso);
  const date = new Date(hasZone ? iso : `${iso}Z`);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}
