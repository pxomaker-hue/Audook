"""Covers endpoints."""

import requests
from flask import Blueprint, Response, jsonify, send_file

from app import CACHE_DIR
from app.api.errors import internal_error
from app.api.sources import MAX_COVER_BYTES, configured_sources, is_public_address, with_server_token
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

    return _fetch_image(cover_url, f"cover for {book_id}")


@bp.route('/api/books/<book_id>/author-photo-proxy', methods=['GET'])
def get_author_photo_proxy(book_id):
    """Same as cover-proxy for the author photo stored in the book metadata
    (Audiobookshelf photo URLs embed the server token)."""
    session = get_session()
    try:
        book = BookRepository(session).get_by_id(book_id)
        photo = (book.extra_metadata or {}).get('author_photo') if book else None
    except Exception as e:
        logger.error(f"Failed to read author photo for {book_id}: {e}")
        return internal_error()
    finally:
        session.close()
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    return _fetch_image(photo, f"author photo for {book_id}")


def _fetch_image(url, what):
    try:
        from urllib.parse import urlparse
        servers_by_host, _ = configured_sources()
        host = urlparse(url).netloc.lower()
        server = servers_by_host.get(host)
        if server is None and (urlparse(url).scheme not in ('http', 'https')
                               or not is_public_address(host)):
            return jsonify({'error': 'Cover not found'}), 404
        if server is not None:
            url = with_server_token(url, server)
        upstream = requests.get(url, timeout=10, stream=True, allow_redirects=False)
        try:
            content_type = upstream.headers.get('Content-Type', '')
            if upstream.status_code != 200 or not content_type.startswith('image/'):
                return jsonify({'error': 'Cover not found'}), 404
            data = b''
            for chunk in upstream.iter_content(chunk_size=65536):
                data += chunk
                if len(data) > MAX_COVER_BYTES:
                    return jsonify({'error': 'Cover not found'}), 404
        finally:
            upstream.close()
        return Response(data, content_type=content_type)
    except Exception as e:
        logger.error(f"Failed to proxy {what}: {e}")
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
