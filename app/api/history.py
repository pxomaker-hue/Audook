"""History endpoints."""

from flask import Blueprint, jsonify

from app.api.errors import internal_error
from app.database import BookRepository, ReadingHistoryRepository, get_session
from app.utils import logger

bp = Blueprint('history', __name__)


@bp.route('/api/history', methods=['GET'])
def get_history():
    try:
        session = get_session()
        history_repo = ReadingHistoryRepository(session)
        book_repo = BookRepository(session)
        sessions = history_repo.get_recent(limit=50)

        results = []
        for entry in sessions:
            book = book_repo.get_by_id(entry.book_id)
            if not book:
                continue
            results.append({
                'session_id': entry.id,
                'book_id': book.id,
                'title': book.title,
                'author': book.author,
                'cover_url': book.cover_url,
                'session_start': entry.session_start.isoformat() if entry.session_start else None,
                'duration_seconds': entry.duration_seconds
            })
        return jsonify(results)
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return internal_error()

@bp.route('/api/history/<int:session_id>', methods=['DELETE'])
def delete_history_entry(session_id):
    try:
        session = get_session()
        deleted = ReadingHistoryRepository(session).delete(session_id)
        if not deleted:
            return jsonify({'error': 'Session introuvable'}), 404
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete history entry: {e}")
        return internal_error()

@bp.route('/api/history', methods=['DELETE'])
def clear_history():
    try:
        session = get_session()
        count = ReadingHistoryRepository(session).delete_all()
        return jsonify({'status': 'cleared', 'deleted': count})
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        return internal_error()
