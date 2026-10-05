"""Collections endpoints."""

from flask import Blueprint, jsonify, request

from app.api.errors import internal_error
from app.database import CollectionRepository, get_session
from app.utils import logger

bp = Blueprint('collections', __name__)


@bp.route('/api/collections', methods=['GET'])
def get_collections():
    try:
        session = get_session()
        collections = CollectionRepository(session).get_all()
        return jsonify([
            {
                'id': c.id,
                'name': c.name,
                'book_ids': c.book_ids or [],
            }
            for c in collections
        ])
    except Exception as e:
        logger.error(f"Failed to get collections: {e}")
        return internal_error()

@bp.route('/api/collections', methods=['POST'])
def create_collection():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Nom requis'}), 400

        session = get_session()
        collection = CollectionRepository(session).create(name)
        return jsonify({'id': collection.id, 'name': collection.name, 'book_ids': []})
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return internal_error()

@bp.route('/api/collections/<collection_id>', methods=['PATCH'])
def rename_collection(collection_id):
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Nom requis'}), 400

        session = get_session()
        collection = CollectionRepository(session).rename(collection_id, name)
        if not collection:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'updated'})
    except Exception as e:
        logger.error(f"Failed to rename collection: {e}")
        return internal_error()

@bp.route('/api/collections/<collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    try:
        session = get_session()
        deleted = CollectionRepository(session).delete(collection_id)
        if not deleted:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        return internal_error()

@bp.route('/api/collections/<collection_id>/books', methods=['POST'])
def add_book_to_collection(collection_id):
    try:
        data = request.json or {}
        book_id = data.get('book_id')
        if not book_id:
            return jsonify({'error': 'book_id requis'}), 400

        session = get_session()
        collection = CollectionRepository(session).add_book(collection_id, book_id)
        if not collection:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'added', 'book_ids': collection.book_ids or []})
    except Exception as e:
        logger.error(f"Failed to add book to collection: {e}")
        return internal_error()

@bp.route('/api/collections/<collection_id>/books/<book_id>', methods=['DELETE'])
def remove_book_from_collection(collection_id, book_id):
    try:
        session = get_session()
        collection = CollectionRepository(session).remove_book(collection_id, book_id)
        if not collection:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'removed', 'book_ids': collection.book_ids or []})
    except Exception as e:
        logger.error(f"Failed to remove book from collection: {e}")
        return internal_error()
