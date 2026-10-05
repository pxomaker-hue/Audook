"""Covers endpoints."""

import requests
from flask import Blueprint, Response, jsonify, send_file

from app import CACHE_DIR
from app.api.errors import internal_error
from app.database import BookRepository, get_session
from app.utils import logger

bp = Blueprint('covers', __name__)


@bp.route('/api/books/<book_id>/cover-proxy', methods=['GET'])
def get_cover_proxy(book_id):
    """Streams a Plex/Audiobookshelf cover through this backend instead of
    the client loading book.cover_url (a direct http:// URL with an
    embedded auth token) itself - the mobile WebView blocks that as mixed
    content even with allowMixedContent set, and this also avoids leaking
    the source server's token to the client."""
    session = get_session()
    try:
        book = BookRepository(session).get_by_id(book_id)
        if not book or not book.cover_url:
            return jsonify({'error': 'Cover not found'}), 404
        cover_url = book.cover_url
    except Exception as e:
        logger.error(f"Failed to proxy cover for {book_id}: {e}")
        return internal_error()
    finally:
        session.close()

    try:
        upstream = requests.get(cover_url, timeout=10, stream=True)
        if upstream.status_code != 200:
            return jsonify({'error': 'Cover not found'}), 404
        return Response(
            upstream.content,
            content_type=upstream.headers.get('Content-Type', 'image/jpeg')
        )
    except Exception as e:
        logger.error(f"Failed to proxy cover for {book_id}: {e}")
        return internal_error()

@bp.route('/api/local-cover/<book_id>', methods=['GET'])
def get_local_cover(book_id):
    """Serves a cover cached by LocalAudiobookScanner (sibling cover file or
    embedded tag art) for a local-folder book - the cover_url stored on
    these books just points here (see app/local/scanner.py:_resolve_cover)."""
    try:
        # Extension isn't known ahead of time (sibling covers keep their
        # original format) - try the common ones the scanner writes.
        for ext in ('jpg', 'jpeg', 'png'):
            candidate = CACHE_DIR / f"local_cover_{book_id}.{ext}"
            if candidate.exists():
                return send_file(candidate)
        return jsonify({'error': 'Cover not found'}), 404
    except Exception as e:
        logger.error(f"Failed to serve local cover for {book_id}: {e}")
        return internal_error()
