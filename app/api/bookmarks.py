"""Bookmarks endpoints."""

from flask import Blueprint, jsonify, request

from app.api.context import services
from app.database import BookmarkRepository, get_session
from app.utils import logger

bp = Blueprint('bookmarks', __name__)


@bp.route('/api/books/<book_id>/bookmarks', methods=['POST'])
def create_bookmark(book_id):
    """Create a bookmark. Defaults to the current playback position if this
    is the book currently playing and no explicit position was given -
    bookmarks persist independently of reading progress, so resetting
    progress never removes them."""
    try:
        book = services.library.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        data = request.json or {}
        chapter_index = data.get('chapter_index')
        position = data.get('position')
        title = data.get('title')

        if chapter_index is None or position is None:
            if services.player.current_audiobook and services.player.current_audiobook.id == book_id:
                chapter_index = services.player.current_chapter_index
                position = services.player.get_current_position()
            else:
                return jsonify({'error': 'chapter_index et position requis (livre non en lecture)'}), 400

        session = get_session()
        bookmark = BookmarkRepository(session).create(book_id, chapter_index, position, title)
        return jsonify({
            'id': bookmark.id,
            'chapter_index': bookmark.chapter_index,
            'position_seconds': bookmark.position_seconds,
            'title': bookmark.title
        }), 201
    except Exception as e:
        logger.error(f"Failed to create bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    try:
        session = get_session()
        BookmarkRepository(session).delete(bookmark_id)
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/bookmarks/<int:bookmark_id>/resume', methods=['POST'])
def resume_bookmark(bookmark_id):
    """Start playback of a book from a saved bookmark's exact position"""
    try:
        session = get_session()
        bookmark = BookmarkRepository(session).get_by_id(bookmark_id)
        if not bookmark:
            return jsonify({'error': 'Bookmark introuvable'}), 404

        book = services.library.get_book_by_id(bookmark.book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        if not services.player.start_playbook(
            book, chapter_index=bookmark.chapter_index, position=bookmark.position_seconds
        ):
            return jsonify({'error': 'La lecture a échoué'}), 500

        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to resume bookmark: {e}")
        return jsonify({'error': str(e)}), 500
