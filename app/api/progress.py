"""Progress endpoints."""


from flask import Blueprint, jsonify, request

from app.database import BookRepository, ReadingProgressRepository, get_session
from app.database.models import Book as DbBook
from app.sync import progress_sync
from app.utils import logger

bp = Blueprint('progress', __name__)


@bp.route('/api/books/<book_id>/progress', methods=['POST'])
def update_book_progress(book_id):
    """Stateless progress update for clients that play audio outside the
    PlayerService singleton (mobile). Persists locally and best-effort
    pushes to the book's source server (Plex/Audiobookshelf), same as the
    desktop player does via PlayerService."""
    try:
        data = request.json or {}
        if 'chapter_index' not in data or 'position_seconds' not in data:
            return jsonify({'error': 'chapter_index and position_seconds are required'}), 400

        chapter_index = int(data['chapter_index'])
        position_seconds = float(data['position_seconds'])

        session = get_session()
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        cumulative = 0.0
        for i, chapter in enumerate(book.chapters or []):
            if i < chapter_index:
                cumulative += chapter.get('duration', 0) or 0
            elif i == chapter_index:
                cumulative += position_seconds
                break
        percent = (cumulative / book.duration * 100) if book.duration else 0.0
        percent = max(0.0, min(100.0, percent))
        finished = percent >= 99.0

        progress_repo = ReadingProgressRepository(session)
        progress_repo.update_progress(book_id, chapter_index, position_seconds, percent)
        if finished:
            progress_repo.set_finished(book_id, True)

        try:
            progress_sync.push_progress(book_id, chapter_index, position_seconds, finished)
        except Exception as e:
            logger.warning(f"Failed to push progress to remote server: {e}")

        return jsonify({'status': 'ok', 'percentage': percent, 'is_finished': finished})
    except Exception as e:
        logger.error(f"Failed to update book progress: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/books/<book_id>/progress', methods=['DELETE'])
def delete_book_progress(book_id):
    """Reset a single book's reading progress (removes it from 'Reprendre l'écoute')"""
    try:
        session = get_session()
        deleted = ReadingProgressRepository(session).delete(book_id)
        if not deleted:
            return jsonify({'error': 'Aucune progression pour ce livre'}), 404

        # A future scan would otherwise re-import this book's still-present
        # progress from its source server (Plex/Audiobookshelf) and put it
        # right back under "Reprendre l'écoute" - flag it as dismissed so
        # the scanner leaves it alone (see scanner.py's
        # _seed_remote_progress_if_new). Real playback progress made after
        # this doesn't go through the scanner, so it's unaffected.
        book = BookRepository(session).get_by_id(book_id)
        if book:
            extra = dict(book.extra_metadata or {})
            extra["progress_dismissed"] = True
            book.extra_metadata = extra
            session.commit()

        return jsonify({'status': 'reset'})
    except Exception as e:
        logger.error(f"Failed to reset book progress: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/progress', methods=['DELETE'])
def clear_all_progress():
    """Reset all reading progress (empties 'Reprendre l'écoute' for every book)"""
    try:
        session = get_session()
        count = ReadingProgressRepository(session).delete_all()
        return jsonify({'status': 'cleared', 'deleted': count})
    except Exception as e:
        logger.error(f"Failed to clear progress: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/progress/dismissed-flags', methods=['DELETE'])
def clear_all_dismissed_flags():
    """One-off maintenance: clears the 'progress_dismissed' flag (set by
    DELETE /api/books/<id>/progress) from every book, so a future scan is
    free to re-import remote progress for all of them again. Use alongside
    DELETE /api/progress when redoing dismissals manually after a bad
    import, rather than being stuck with old dismiss decisions forever."""
    try:
        session = get_session()
        books = session.query(DbBook).all()
        cleared = 0
        for book in books:
            extra = book.extra_metadata or {}
            if extra.get('progress_dismissed'):
                extra = dict(extra)
                del extra['progress_dismissed']
                book.extra_metadata = extra
                cleared += 1
        session.commit()
        return jsonify({'status': 'cleared', 'books_affected': cleared})
    except Exception as e:
        logger.error(f"Failed to clear dismissed flags: {e}")
        return jsonify({'error': str(e)}), 500
