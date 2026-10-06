import React from 'react';
import { Play } from 'lucide-react';
import { BookDetail } from './types';

interface ChapterListProps {
  book: BookDetail;
  activeChapterIndex: number | null;
  activePosition: number;
  onPlayChapter: (chapterIndex: number) => void;
}

const ChapterList: React.FC<ChapterListProps> = ({ book, activeChapterIndex, activePosition, onPlayChapter }) => {
  const chapters = book.chapters || [];
  if (chapters.length === 0) return null;

  // While actively playing this book, use the live polled position;
  // otherwise fall back to the last saved progress - either way, chapters
  // before that point read as fully listened, the current one shows its own
  // fraction, and later ones are untouched.
  const referenceChapterIndex = activeChapterIndex ?? book.progress.chapter_index;
  const referencePosition = activeChapterIndex !== null ? activePosition : book.progress.position;

  return (
    <section>
      <h2 className="bd-heading">Chapitres</h2>
      <div className="bd-chapters-header" aria-hidden="true">
        <span>Titre</span>
        <span>Durée</span>
      </div>
      <ul className="bd-list bd-list-bordered">
        {chapters.map((chapter, index) => {
          const isActive = activeChapterIndex === index;
          const progress = index < referenceChapterIndex
            ? 100
            : index === referenceChapterIndex && chapter.duration > 0
            ? Math.min(100, (referencePosition / chapter.duration) * 100)
            : 0;
          return (
            <li key={chapter.id} className="bd-chapter-wrap">
              <button
                type="button"
                className={`bd-chapter ${isActive ? 'active' : ''}`}
                onClick={() => onPlayChapter(index)}
                aria-current={isActive ? 'true' : undefined}
              >
                {progress > 0 && <span className="bd-chapter-progress" style={{ width: `${progress}%` }} />}
                <span className="bd-chapter-main">
                  <span className="bd-chapter-icon">
                    <Play size={13} fill="currentColor" />
                  </span>
                  <span className="bd-ellipsis">
                    {index + 1}. {chapter.title}
                  </span>
                </span>
                <span className="bd-chapter-duration">{Math.floor(chapter.duration / 60)}m</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
};

export default ChapterList;
