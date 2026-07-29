import { useEffect, useState } from 'react';

// Tracks whether the mobile full-screen player overlay is showing, so
// Player.tsx (sets it on cover tap) and Sidebar.tsx (reads it to render as a
// compact bottom bar, and resets it on navigation) can share it without a
// common parent re-render - same singleton pattern as mobilePlayerStore.
type Listener = (expanded: boolean) => void;

let expanded = false;
const listeners = new Set<Listener>();

function setExpanded(value: boolean) {
  if (expanded === value) return;
  expanded = value;
  listeners.forEach((l) => l(expanded));
}

function toggleExpanded() {
  setExpanded(!expanded);
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const expandedPlayerStore = { setExpanded, toggleExpanded, subscribe };

export function useExpandedPlayer(): boolean {
  const [value, setValue] = useState(expanded);
  useEffect(() => {
    return expandedPlayerStore.subscribe(setValue);
  }, []);
  return value;
}
