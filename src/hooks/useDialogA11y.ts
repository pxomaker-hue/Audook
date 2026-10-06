import { useEffect, useRef } from 'react';

// Modal basics shared by the app's dialogs: move focus inside on open, trap
// Tab within the dialog, close on Escape, and hand focus back to whatever
// opened it. Attach the returned ref to the element with role="dialog".
export function useDialogA11y<T extends HTMLElement>(open: boolean, onEscape?: () => void) {
  const ref = useRef<T>(null);
  const escapeRef = useRef(onEscape);
  escapeRef.current = onEscape;

  useEffect(() => {
    if (!open || !ref.current) return;
    const dialog = ref.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(dialog.querySelectorAll<HTMLElement>('button, input, [href], [tabindex]:not([tabindex="-1"])'))
        .filter((el) => !el.hasAttribute('disabled'));

    focusables()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && escapeRef.current) {
        e.stopPropagation();
        escapeRef.current();
      } else if (e.key === 'Tab') {
        const items = focusables();
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open]);

  return ref;
}
