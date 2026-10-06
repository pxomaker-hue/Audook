import React from 'react';
import { Bookmark, Loader2, Pencil, Trash2 } from 'lucide-react';
import { formatBookmarkDate, formatBookmarkPosition } from '../../bookmarkFormat';
import { BookDetail, BookmarkEntry } from './types';

interface BookmarkListProps {
  book: BookDetail;
  resumingBookmarkId: number | null;
  onResume: (bookmark: BookmarkEntry) => void;
  onRename: (bookmark: BookmarkEntry) => void;
  onDelete: (bookmarkId: number) => void;
}

const BookmarkList: React.FC<BookmarkListProps> = ({ book, resumingBookmarkId, onResume, onRename, onDelete }) => {
  const bookmarks = book.bookmarks || [];

  return (
    <section className="bd-section">
      <h2 className="bd-heading">Marque-pages</h2>

      {bookmarks.length === 0 ? (
        <p className="bd-muted">Aucun marque-page pour ce livre.</p>
      ) : (
        <ul className="bd-list">
          {bookmarks.map((bookmark) => {
            const chapter = (book.chapters || [])[bookmark.chapter_index];
            const date = formatBookmarkDate(bookmark.created_at);
            const resuming = resumingBookmarkId === bookmark.id;
            return (
              <li key={bookmark.id} className="bd-list-item">
                <Bookmark size={16} color="var(--primary)" fill="var(--primary)" className="bd-no-shrink" aria-hidden="true" />
                <div className="bd-grow">
                  <div className="bd-item-title">
                    {bookmark.title || chapter?.title || `Chapitre ${bookmark.chapter_index + 1}`}
                  </div>
                  <div className="bd-item-meta">
                    {bookmark.title && chapter?.title ? `${chapter.title} · ` : ''}
                    {formatBookmarkPosition(bookmark.position_seconds)}
                    {date ? ` · ${date}` : ''}
                  </div>
                </div>
                <button
                  type="button"
                  className="cta-button bd-button bd-button-compact"
                  disabled={resuming}
                  onClick={() => onResume(bookmark)}
                >
                  {resuming ? <Loader2 size={14} className="spin" /> : 'Reprendre'}
                </button>
                <button
                  type="button"
                  className="bd-icon-button"
                  onClick={() => onRename(bookmark)}
                  title="Renommer ce marque-page"
                  aria-label="Renommer ce marque-page"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="bd-icon-button"
                  onClick={() => onDelete(bookmark.id)}
                  title="Supprimer ce marque-page"
                  aria-label="Supprimer ce marque-page"
                >
                  <Trash2 size={15} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};

export default BookmarkList;
