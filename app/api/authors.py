"""Authors endpoints."""

from flask import Blueprint, jsonify, request

from app.api.errors import internal_error
from app.database import BookRepository, get_session
from app.utils import logger, online_metadata

bp = Blueprint('authors', __name__)


@bp.route('/api/authors/<name>', methods=['PATCH'])
def update_author(name):
    """Manually edit an author's bio/photo. Since authors aren't a separate
    table, this applies to every book currently attributed to that exact
    author string."""
    try:
        data = request.json or {}
        fields = {}
        if 'bio' in data:
            fields['author_bio'] = data['bio']
        if 'photo' in data:
            fields['author_photo'] = data['photo']
        if not fields:
            return jsonify({'error': 'Aucun champ valide à mettre à jour'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        books = book_repo.get_by_author(name)
        if not books:
            return jsonify({'error': 'Auteur introuvable'}), 404

        for book in books:
            book_repo.update_fields(book.id, fields, lock=True)

        return jsonify({'status': 'updated', 'books_updated': len(books)})
    except Exception as e:
        logger.error(f"Failed to update author: {e}")
        return internal_error()

@bp.route('/api/authors/<name>/refresh', methods=['POST'])
def refresh_author(name):
    """Force a fresh online lookup for an author (French Wikipedia first),
    overwriting any existing bio/photo, and apply it to every book by that
    author."""
    try:
        session = get_session()
        book_repo = BookRepository(session)
        books = book_repo.get_by_author(name)
        if not books:
            return jsonify({'error': 'Auteur introuvable'}), 404

        info = online_metadata.fetch_author_info_online(name, force=True)
        if not info.get('bio') and not info.get('photo'):
            return jsonify({'status': 'not_found', 'bio': None, 'photo': None})

        fields = {}
        if info.get('bio'):
            fields['author_bio'] = info['bio']
        if info.get('photo'):
            fields['author_photo'] = info['photo']

        for book in books:
            book_repo.update_fields(book.id, fields, lock=True)

        return jsonify({'status': 'updated', 'bio': info.get('bio'), 'photo': info.get('photo')})
    except Exception as e:
        logger.error(f"Failed to refresh author: {e}")
        return internal_error()
