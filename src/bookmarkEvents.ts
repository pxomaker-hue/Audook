// The player (docked bar, full-screen mobile player, mini-player) and the book
// page are separate React trees with separate state - this tiny event lets the
// book page refresh its bookmark list the moment one is added from the player.
export const BOOKMARKS_CHANGED_EVENT = 'audook:bookmarks-changed';

export function notifyBookmarksChanged(): void {
  window.dispatchEvent(new Event(BOOKMARKS_CHANGED_EVENT));
}
