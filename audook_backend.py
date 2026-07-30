#!/usr/bin/env python3
"""
Audook Backend - Exposes services via HTTP API for Electron frontend
"""

import os
import sys
import re
import threading
from pathlib import Path
import asyncio
import requests
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database, get_session, remove_session, BookRepository, ReadingProgressRepository, ReadingHistoryRepository, ServerRepository, BookmarkRepository, EqualizerPresetRepository, AppSettingsRepository, CollectionRepository
from app.services import LibraryService, PlayerService, SyncService
from app.sync.scanner import scanner
from app.sync import progress_sync
from app.clients import PlexClient, AudiobookshelfClient
from app.local import LocalClient
from app.utils import logger, generate_id, online_metadata, audio_loudness
from app.database.models import Book as DbBook
from app import CACHE_DIR

app = Flask(__name__)
CORS(app)

# Initialize services
library_service = None
player_service = None
sync_service = None


def format_chapter_title(index, title):
    """Prefix the chapter number before its title wherever the "currently
    playing chapter" is shown - some sources (and our own fallback naming)
    give every chapter the same/generic title, which is otherwise
    impossible to tell apart on the player."""
    if title is None:
        return None
    return f"{index + 1}. {title}"

# Health check endpoint for Electron app (before services init)
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.teardown_appcontext
def cleanup_db_session(exception=None):
    # Almost none of the routes below call session.close() themselves - this
    # returns the connection to the pool at the end of every request instead
    # of leaking it, which otherwise exhausts SQLAlchemy's default pool
    # (size 5 + 10 overflow) within seconds under mobile's frequent polling.
    remove_session()

@app.before_request
def init_services():
    # Skip for health check endpoint
    if request.path == '/health':
        return

    global library_service, player_service, sync_service
    if library_service is None:
        try:
            library_service = LibraryService()
            player_service = PlayerService()
            sync_service = SyncService()
            player_service.restore_audio_settings()
            # Auto-sync once on startup so "Reprendre l'écoute" reflects
            # progress made elsewhere (mobile, ABS/Plex web player) without
            # needing to remember to hit "Synchroniser" first - runs in the
            # background (same call the manual sync button uses), so it
            # never delays the app becoming usable.
            sync_service.sync_all_servers(background=True)
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            # Continue anyway - services will be retried on next request
            pass

# Server management endpoints
def _normalize_server_url(server_type, url):
    """Prepend http:// when the user omitted the scheme (Plex/Audiobookshelf only)"""
    if server_type in ('plex', 'audiobookshelf') and not url.lower().startswith(('http://', 'https://')):
        return f"http://{url}"
    return url


def _test_server_connection(server_type, url, api_key=None, username=None, password=None):
    """Attempt to connect to a server, return (ok, error_message)"""
    try:
        if server_type == "plex":
            client = PlexClient(url, api_key)
            return client.test_connection(), None
        elif server_type == "audiobookshelf":
            client = AudiobookshelfClient(url, username, password)
            return client.test_connection(), None
        elif server_type == "local":
            client = LocalClient(url)
            return asyncio.run(client.ping()), None
        else:
            return False, f"Unknown server type: {server_type}"
    except Exception as e:
        return False, str(e)


@app.route('/api/servers', methods=['GET'])
def get_servers():
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        servers = server_repo.get_all()
        return jsonify([{
            'id': s.id,
            'type': s.type,
            'name': s.name,
            'url': s.url,
            'remote_url': s.remote_url,
            'use_remote': s.use_remote,
            'hidden': s.hidden,
            'sync_enabled': s.sync_enabled,
            'last_sync': s.last_sync.isoformat() if s.last_sync else None
        } for s in servers])
    except Exception as e:
        logger.error(f"Failed to get servers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers', methods=['POST'])
def add_server():
    try:
        data = request.json or {}
        server_type = data.get('type')
        name = data.get('name')
        url = data.get('url')

        if server_type not in ('plex', 'audiobookshelf', 'local'):
            return jsonify({'error': 'Type de serveur invalide'}), 400
        if not name or not url:
            return jsonify({'error': 'Nom et URL/chemin requis'}), 400

        url = _normalize_server_url(server_type, url)
        api_key = data.get('api_key')
        username = data.get('username')
        password = data.get('password')
        remote_url = data.get('remote_url') or None
        if remote_url:
            remote_url = _normalize_server_url(server_type, remote_url)

        ok, error = _test_server_connection(server_type, url, api_key, username, password)
        if not ok:
            return jsonify({'error': error or 'Connexion impossible'}), 400

        session = get_session()
        server_repo = ServerRepository(session)
        server = server_repo.create(
            server_id=generate_id(f"{server_type}_"),
            type=server_type,
            name=name,
            url=url,
            api_key=api_key,
            username=username,
            password=password,
            remote_url=remote_url
        )

        return jsonify({
            'id': server.id,
            'type': server.type,
            'name': server.name,
            'url': server.url,
            'remote_url': server.remote_url,
            'use_remote': server.use_remote
        }), 201
    except Exception as e:
        logger.error(f"Failed to add server: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<server_id>', methods=['DELETE'])
def delete_server(server_id):
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        server_repo.delete(server_id)
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete server: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<server_id>/remote-access', methods=['POST'])
def set_server_remote_access(server_id):
    """Audiobookshelf only: set the remote-reachable address and/or flip
    the local/remote toggle. Note: chapter streaming URLs already scanned
    into the library were built from whichever address was active at scan
    time - switching this only affects new scans, not books already synced;
    re-scan the server after switching to refresh them."""
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        server = server_repo.get_by_id(server_id)
        if not server:
            return jsonify({'error': 'Serveur introuvable'}), 404
        if server.type != 'audiobookshelf':
            return jsonify({'error': "L'accès distant ne se règle que pour Audiobookshelf (Plex bascule automatiquement)"}), 400

        data = request.json or {}
        use_remote = data.get('use_remote')

        if 'remote_url' in data:
            remote_url = data.get('remote_url')
            if remote_url:
                remote_url = _normalize_server_url(server.type, remote_url)
            updated = server_repo.set_remote_access(
                server_id, remote_url=remote_url,
                use_remote=bool(use_remote) if use_remote is not None else None
            )
        else:
            updated = server_repo.set_remote_access(
                server_id, use_remote=bool(use_remote) if use_remote is not None else None
            )
        return jsonify({
            'id': updated.id,
            'remote_url': updated.remote_url,
            'use_remote': updated.use_remote
        })
    except Exception as e:
        logger.error(f"Failed to set remote access: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<server_id>/hidden', methods=['POST'])
def set_server_hidden(server_id):
    """Show/hide this server's books in the library views - purely a
    display filter, doesn't touch any synced data (see GET /api/books)."""
    try:
        data = request.json or {}
        session = get_session()
        updated = ServerRepository(session).set_hidden(server_id, bool(data.get('hidden')))
        if not updated:
            return jsonify({'error': 'Serveur introuvable'}), 404
        return jsonify({'id': updated.id, 'hidden': updated.hidden})
    except Exception as e:
        logger.error(f"Failed to set server hidden state: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<server_id>/test', methods=['POST'])
def test_server(server_id):
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        server = server_repo.get_by_id(server_id)
        if not server:
            return jsonify({'error': 'Serveur introuvable'}), 404

        ok, error = _test_server_connection(
            server.type, server.url, server.api_key, server.username, server.password
        )
        return jsonify({'connected': ok, 'error': error})
    except Exception as e:
        logger.error(f"Failed to test server: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<server_id>/scan', methods=['POST'])
def scan_server(server_id):
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        server = server_repo.get_by_id(server_id)
        if not server:
            return jsonify({'error': 'Serveur introuvable'}), 404

        success = scanner.scan_server(server)
        return jsonify({'status': 'scanned' if success else 'failed'})
    except Exception as e:
        logger.error(f"Failed to scan server: {e}")
        return jsonify({'error': str(e)}), 500

# Library endpoints
@app.route('/api/books', methods=['GET'])
def get_books():
    try:
        books = library_service.get_all_books()
        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        in_progress = progress_repo.get_in_progress_map()
        finished_ids = progress_repo.get_finished_book_ids()
        bookmarked_ids = BookmarkRepository(session).get_book_ids_with_bookmarks()

        # Books from a hidden server are excluded from library views - the
        # synced data itself is untouched, this is purely a display filter
        # (see POST /api/servers/<id>/hidden).
        hidden_server_ids = ServerRepository(session).get_hidden_server_ids()
        if hidden_server_ids:
            hidden_book_ids = {
                row[0] for row in session.query(DbBook.id)
                .filter(DbBook.server_id.in_(hidden_server_ids)).all()
            }
            books = [b for b in books if b.id not in hidden_book_ids]

        result = []
        for book in books:
            progress = in_progress.get(book.id)
            current_chapter_title = None
            if progress and book.chapters:
                chapter_index = progress.get('chapter_index') or 0
                if 0 <= chapter_index < len(book.chapters):
                    current_chapter_title = format_chapter_title(chapter_index, book.chapters[chapter_index].get('title'))

            result.append({
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'narrator': book.narrator,
                'cover_url': book.cover,
                'duration': book.duration,
                'description': book.description,
                'source': book.source,
                'series': book.metadata.get('series'),
                'series_sequence': book.metadata.get('series_sequence'),
                'genre': book.metadata.get('genre') or [],
                'progress_percent': progress.get('percent') if progress else 0,
                'current_chapter_title': current_chapter_title,
                'is_finished': book.id in finished_ids,
                'has_bookmark': book.id in bookmarked_ids,
                'author_bio': book.metadata.get('author_bio'),
                'author_photo': book.metadata.get('author_photo')
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get books: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>', methods=['GET'])
def get_book_details(book_id):
    try:
        book = library_service.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        try:
            progress_sync.reconcile_progress(book_id)
        except Exception as e:
            logger.warning(f"Failed to reconcile progress before returning book details: {e}")

        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        progress = progress_repo.get_or_create(book_id)
        bookmarks = BookmarkRepository(session).get_by_book(book_id)

        return jsonify({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover,
            'duration': book.duration,
            'description': book.description,
            'chapters': book.chapters,
            'series': book.metadata.get('series'),
            'series_sequence': book.metadata.get('series_sequence'),
            'genre': book.metadata.get('genre') or [],
            'author_bio': book.metadata.get('author_bio'),
            'author_photo': book.metadata.get('author_photo'),
            'manual_overrides': book.metadata.get('manual_overrides', []),
            'progress': {
                'position': progress.position_seconds,
                'percentage': progress.progress_percent,
                'chapter_index': progress.current_chapter_index
            },
            'is_finished': progress.is_finished,
            'noise_reduction_status': BookRepository(session).get_noise_reduction_status(book_id),
            'use_cleaned_audio': BookRepository(session).get_use_cleaned_audio(book_id),
            'bookmarks': [{
                'id': b.id,
                'chapter_index': b.chapter_index,
                'position_seconds': b.position_seconds,
                'title': b.title,
                'created_at': b.created_at.isoformat() if b.created_at else None
            } for b in bookmarks]
        })
    except Exception as e:
        logger.error(f"Failed to get book details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/finished', methods=['POST'])
def set_book_finished(book_id):
    """Manually mark/unmark a book as finished. Also best-effort pushes the
    finished status to the book's source server (Plex/Audiobookshelf)."""
    try:
        data = request.json or {}
        finished = bool(data.get('finished', True))

        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        progress = progress_repo.set_finished(book_id, finished)
        chapter_index = progress.current_chapter_index
        position = progress.position_seconds

        try:
            progress_sync.push_progress(book_id, chapter_index, position, finished)
        except Exception as e:
            logger.warning(f"Failed to push finished status to remote server: {e}")

        return jsonify({'status': 'ok', 'is_finished': finished})
    except Exception as e:
        logger.error(f"Failed to set finished status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/progress', methods=['POST'])
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

@app.route('/api/books/<book_id>/clean-audio', methods=['POST'])
def clean_book_audio(book_id):
    """Kick off a one-time, opt-in noise-reduction pass over this book's
    chapters (see PlayerService.start_noise_reduction). Runs in the
    background - the caller polls GET /api/books/<id> for
    noise_reduction_status ('processing' -> 'done'/'error')."""
    try:
        book = library_service.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        started = player_service.start_noise_reduction(book_id)
        if not started:
            return jsonify({'status': 'already_processing'})
        return jsonify({'status': 'processing'})
    except Exception as e:
        logger.error(f"Failed to start noise reduction: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/use-cleaned-audio', methods=['POST'])
def set_book_use_cleaned_audio(book_id):
    """Switch a book back to its original audio, or back to the cleaned
    version - the cleaned files stay cached either way, so flipping this
    is instant and doesn't require re-running the noise reduction pass."""
    try:
        data = request.json or {}
        enabled = bool(data.get('enabled', True))
        session = get_session()
        BookRepository(session).set_use_cleaned_audio(book_id, enabled)
        return jsonify({'status': 'ok', 'use_cleaned_audio': enabled})
    except Exception as e:
        logger.error(f"Failed to set use_cleaned_audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/bookmarks', methods=['POST'])
def create_bookmark(book_id):
    """Create a bookmark. Defaults to the current playback position if this
    is the book currently playing and no explicit position was given -
    bookmarks persist independently of reading progress, so resetting
    progress never removes them."""
    try:
        book = library_service.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        data = request.json or {}
        chapter_index = data.get('chapter_index')
        position = data.get('position')
        title = data.get('title')

        if chapter_index is None or position is None:
            if player_service.current_audiobook and player_service.current_audiobook.id == book_id:
                chapter_index = player_service.current_chapter_index
                position = player_service.get_current_position()
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

@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    try:
        session = get_session()
        BookmarkRepository(session).delete(bookmark_id)
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookmarks/<int:bookmark_id>/resume', methods=['POST'])
def resume_bookmark(bookmark_id):
    """Start playback of a book from a saved bookmark's exact position"""
    try:
        session = get_session()
        bookmark = BookmarkRepository(session).get_by_id(bookmark_id)
        if not bookmark:
            return jsonify({'error': 'Bookmark introuvable'}), 404

        book = library_service.get_book_by_id(bookmark.book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        if not player_service.start_playbook(
            book, chapter_index=bookmark.chapter_index, position=bookmark.position_seconds
        ):
            return jsonify({'error': 'La lecture a échoué'}), 500

        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to resume bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>', methods=['PATCH'])
def update_book(book_id):
    """Manually edit a book's metadata. Edited fields are locked against
    being overwritten by a future scan."""
    try:
        data = request.json or {}
        allowed_fields = ('title', 'author', 'narrator', 'description', 'cover_url', 'series', 'genre')
        fields = {k: v for k, v in data.items() if k in allowed_fields}
        if not fields:
            return jsonify({'error': 'Aucun champ valide à mettre à jour'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.update_fields(book_id, fields, lock=True)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'updated'})
    except Exception as e:
        logger.error(f"Failed to update book: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/lock', methods=['POST'])
def lock_book_fields(book_id):
    """Lock fields against being overwritten by a future scan or online
    match/replace, without changing their value - lets the user freely lock
    a field, not just get it locked as a side effect of editing it."""
    try:
        data = request.json or {}
        fields = data.get('fields')
        if not fields or not isinstance(fields, list):
            return jsonify({'error': 'fields (liste) requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.lock_fields(book_id, fields)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'locked', 'fields': fields})
    except Exception as e:
        logger.error(f"Failed to lock book fields: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/unlock', methods=['POST'])
def unlock_book_fields(book_id):
    """Unlock previously-manually-edited fields so the next scan or online
    match/replace can overwrite them again."""
    try:
        data = request.json or {}
        fields = data.get('fields')
        if not fields or not isinstance(fields, list):
            return jsonify({'error': 'fields (liste) requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.unlock_fields(book_id, fields)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'unlocked', 'fields': fields})
    except Exception as e:
        logger.error(f"Failed to unlock book fields: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/match-candidates', methods=['GET'])
def get_book_match_candidates(book_id):
    """Search Open Library for candidate matches for a book (like Plex's
    'Fix Match'). Defaults to the book's own title/author but accepts an
    override query for a manual search."""
    try:
        book = library_service.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        query = request.args.get('query', '').strip()
        # Local-folder scans sometimes fall back to the raw filename/folder
        # name as the title (e.g. "Harry_Potter_a_L_Ecole_des_sorciers"),
        # which searches poorly - clean it up before using it as a query.
        title = query or re.sub(r'[_\s]+', ' ', book.title).strip()
        author = None if query else book.author

        # Fetch more than the usual default so the frontend has enough
        # Open Library/Google Books results in reserve for its "Voir plus"
        # button (Audible results are shown first/by default, these are
        # extra/optional since audiobooks rarely need them).
        candidates = online_metadata.search_book_candidates(title, author, limit=12)
        return jsonify(candidates)
    except Exception as e:
        logger.error(f"Failed to get match candidates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/match', methods=['POST'])
def apply_book_match(book_id):
    """Apply a chosen Open Library candidate to a book. mode='replace'
    overwrites description/cover unconditionally, mode='fill' (default)
    only fills fields that are currently empty."""
    try:
        data = request.json or {}
        work_key = data.get('work_key')
        mode = data.get('mode', 'fill')
        # The candidate's title/author come from the search result itself
        # (search_book_candidates), not from get_book_work_details below -
        # that only fetches description/cover/genre, so without these the
        # title/author shown in the search list never actually got applied.
        candidate_title = (data.get('title') or '').strip()
        candidate_author = (data.get('author') or '').strip()
        if not work_key:
            return jsonify({'error': 'work_key requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        details = online_metadata.get_book_work_details(work_key)
        existing_metadata = book.extra_metadata or {}
        existing_genre = existing_metadata.get('genre') or []
        locked_fields = set(existing_metadata.get('manual_overrides') or [])

        def should_apply(field_name, existing_value, candidate_value):
            """Compléter (fill): only touches fields that are currently
            empty, and never touches a locked field even if it's empty (a
            locked-but-empty field means the user deliberately wants it left
            blank). Remplacer (replace): overwrites regardless of whether
            it's already filled, but a locked field is still protected -
            that's the whole point of locking it."""
            if not candidate_value or field_name in locked_fields:
                return False
            return mode == 'replace' or not existing_value

        fields = {}
        if should_apply('title', book.title, candidate_title):
            fields['title'] = candidate_title
        if should_apply('author', book.author, candidate_author):
            fields['author'] = candidate_author
        if should_apply('description', book.description, details.get('description')):
            fields['description'] = details['description']
        if should_apply('cover_url', book.cover_url, details.get('cover_url')):
            fields['cover_url'] = details['cover_url']
        if should_apply('genre', existing_genre, details.get('genre')):
            fields['genre'] = [details['genre']]
        # Audible-only fields: narrator/series/series_sequence - Open
        # Library/Google Books candidates never populate these (they're
        # book-catalog databases, not audiobook ones), so this is a no-op
        # for any match that didn't come from Audible.
        if should_apply('narrator', book.narrator, details.get('narrator')):
            fields['narrator'] = details['narrator']
        if should_apply('series', existing_metadata.get('series'), details.get('series')):
            fields['series'] = details['series']
        if should_apply('series_sequence', existing_metadata.get('series_sequence'), details.get('series_sequence')):
            fields['series_sequence'] = details['series_sequence']

        applied = []
        if fields:
            book_repo.update_fields(book_id, fields, lock=True)
            applied.extend(fields.keys())

        # Real per-chapter titles - only from Audible (the only source with
        # actual chapter data), and only applied when the chapter count
        # matches exactly (see update_chapter_titles). Not part of the
        # fill/replace/lock field system above since there's nothing to lock
        # a chapter title against - a matching chapter count is itself the
        # safety check.
        if work_key.startswith('audible:'):
            chapters = online_metadata.get_audible_chapters(work_key[len('audible:'):])
            if chapters:
                titles = [c['title'] for c in chapters if c.get('title')]
                if len(titles) == len(book.chapters or []) and book_repo.update_chapter_titles(book_id, titles):
                    applied.append('chapters')

        if not applied:
            return jsonify({'status': 'no_change'})

        return jsonify({'status': 'matched', 'applied': applied})
    except Exception as e:
        logger.error(f"Failed to apply match: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/authors/<name>', methods=['PATCH'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/authors/<name>/refresh', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<int:session_id>', methods=['DELETE'])
def delete_history_entry(session_id):
    try:
        session = get_session()
        deleted = ReadingHistoryRepository(session).delete(session_id)
        if not deleted:
            return jsonify({'error': 'Session introuvable'}), 404
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete history entry: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    try:
        session = get_session()
        count = ReadingHistoryRepository(session).delete_all()
        return jsonify({'status': 'cleared', 'deleted': count})
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections', methods=['GET'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections/<collection_id>', methods=['PATCH'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections/<collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    try:
        session = get_session()
        deleted = CollectionRepository(session).delete(collection_id)
        if not deleted:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections/<collection_id>/books', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections/<collection_id>/books/<book_id>', methods=['DELETE'])
def remove_book_from_collection(collection_id, book_id):
    try:
        session = get_session()
        collection = CollectionRepository(session).remove_book(collection_id, book_id)
        if not collection:
            return jsonify({'error': 'Collection introuvable'}), 404
        return jsonify({'status': 'removed', 'book_ids': collection.book_ids or []})
    except Exception as e:
        logger.error(f"Failed to remove book from collection: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/progress', methods=['DELETE'])
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

@app.route('/api/progress', methods=['DELETE'])
def clear_all_progress():
    """Reset all reading progress (empties 'Reprendre l'écoute' for every book)"""
    try:
        session = get_session()
        count = ReadingProgressRepository(session).delete_all()
        return jsonify({'status': 'cleared', 'deleted': count})
    except Exception as e:
        logger.error(f"Failed to clear progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress/dismissed-flags', methods=['DELETE'])
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

@app.route('/api/books/search', methods=['GET'])
def search_books():
    try:
        query = request.args.get('q', '')
        books = library_service.search_books(query)
        return jsonify([{
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover
        } for book in books])
    except Exception as e:
        logger.error(f"Failed to search books: {e}")
        return jsonify({'error': str(e)}), 500

# Player endpoints
@app.route('/api/player/play', methods=['POST'])
def play_book():
    try:
        data = request.json
        book_id = data.get('book_id')
        chapter_index = data.get('chapter_index')
        audiobook = library_service.get_book_by_id(book_id)
        if not audiobook:
            return jsonify({'error': 'Book not found'}), 404
        if not player_service.start_playbook(audiobook, chapter_index=chapter_index):
            return jsonify({'error': 'La lecture a échoué (voir les logs du serveur)'}), 500
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to play book: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/pause', methods=['POST'])
def pause_playback():
    try:
        player_service.pause()
        return jsonify({'status': 'paused'})
    except Exception as e:
        logger.error(f"Failed to pause: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/resume', methods=['POST'])
def resume_playback():
    try:
        player_service.resume()
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to resume: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/stop', methods=['POST'])
def stop_playback():
    try:
        player_service.stop()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"Failed to stop: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/next-chapter', methods=['POST'])
def next_chapter():
    try:
        if not player_service.next_chapter():
            return jsonify({'error': 'Pas de chapitre suivant'}), 400
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to go to next chapter: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/previous-chapter', methods=['POST'])
def previous_chapter():
    try:
        if not player_service.previous_chapter():
            return jsonify({'error': 'Pas de chapitre précédent'}), 400
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to go to previous chapter: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/seek', methods=['POST'])
def seek():
    try:
        data = request.json
        position = data.get('position')
        player_service.seek(position)
        return jsonify({'status': 'seeking'})
    except Exception as e:
        logger.error(f"Failed to seek: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/volume', methods=['POST'])
def set_volume():
    try:
        data = request.json
        volume = data.get('volume')
        player_service.set_volume(volume)
        return jsonify({'status': 'volume_set'})
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/speed', methods=['POST'])
def set_speed():
    try:
        data = request.json
        speed = data.get('speed')
        player_service.set_speed(speed)
        return jsonify({'status': 'speed_set'})
    except Exception as e:
        logger.error(f"Failed to set speed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/equalizer', methods=['POST'])
def set_player_equalizer():
    try:
        data = request.json or {}
        preset_id = data.get('preset_id')
        if preset_id is None:
            player_service.set_equalizer_preset(None)
            return jsonify({'status': 'equalizer_set', 'preset_id': None})

        session = get_session()
        preset = EqualizerPresetRepository(session).get_by_id(preset_id)
        session.close()
        if not preset:
            return jsonify({'error': 'Preset introuvable'}), 404

        player_service.set_equalizer_preset(preset.id, preset.bands, preset.preamp)
        return jsonify({'status': 'equalizer_set', 'preset_id': preset.id})
    except Exception as e:
        logger.error(f"Failed to set equalizer: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/equalizer/cycle', methods=['POST'])
def cycle_player_equalizer():
    try:
        new_preset_id = player_service.cycle_equalizer_preset()
        return jsonify({'status': 'equalizer_cycled', 'preset_id': new_preset_id})
    except Exception as e:
        logger.error(f"Failed to cycle equalizer: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/compression/cycle', methods=['POST'])
def cycle_player_compression():
    """Cycle dynamic range compression: off -> léger -> modéré -> fort ->
    off (see VLCPlayer.COMPRESSOR_PRESETS)."""
    try:
        new_preset = player_service.cycle_compression()
        return jsonify({'status': 'compression_cycled', 'preset': new_preset})
    except Exception as e:
        logger.error(f"Failed to cycle compression: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/loudness-normalization', methods=['POST'])
def set_player_loudness_normalization():
    """Toggle per-book EBU-style loudness matching (see
    app/utils/audio_loudness.py) - distinct from the real-time
    'Normalisation' filter above."""
    try:
        data = request.json or {}
        enabled = bool(data.get('enabled'))
        player_service.set_loudness_normalization(enabled)
        return jsonify({'status': 'loudness_normalization_set', 'enabled': enabled})
    except Exception as e:
        logger.error(f"Failed to set loudness normalization: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/sleep-timer', methods=['POST'])
def set_player_sleep_timer():
    """Set (or cancel, with minutes null/0) the sleep timer. Fades the
    volume out and pauses playback once it elapses - see
    PlayerService.set_sleep_timer."""
    try:
        data = request.json or {}
        minutes = data.get('minutes')
        player_service.set_sleep_timer(minutes)
        return jsonify({
            'status': 'ok',
            'sleep_timer_remaining_seconds': player_service.get_sleep_timer_remaining_seconds()
        })
    except Exception as e:
        logger.error(f"Failed to set sleep timer: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/loudness-gain', methods=['GET'])
def get_book_loudness_gain(book_id):
    """Per-book EBU-style loudness gain (see app/utils/audio_loudness.py) -
    used by the mobile app to apply the same normalization desktop does via
    VLC's equalizer preamp, through Android's LoudnessEnhancer/volume
    instead. Returns the cached value immediately if there is one;
    otherwise kicks off the (slow, ffmpeg-based) measurement in the
    background - same as the desktop player does on first play of a book -
    and returns null so the caller can poll again shortly after."""
    try:
        session = get_session()
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        cached_gain = BookRepository(session).get_loudness_gain(book_id)
        if cached_gain is not None:
            return jsonify({'gain_db': cached_gain})

        chapters = book.chapters or []
        source = chapters[0].get('audio_file') if chapters else None
        if not source:
            return jsonify({'gain_db': None})

        def measure_and_cache():
            gain = audio_loudness.measure_loudness_gain(source)
            if gain is None:
                return
            measure_session = get_session()
            try:
                BookRepository(measure_session).set_loudness_gain(book_id, gain)
            finally:
                measure_session.close()

        threading.Thread(target=measure_and_cache, daemon=True).start()
        return jsonify({'gain_db': None})
    except Exception as e:
        logger.error(f"Failed to get loudness gain for {book_id}: {e}")
        return jsonify({'error': str(e)}), 500

# Equalizer preset management (fine-tuning lives in Settings)
@app.route('/api/equalizer/presets', methods=['GET'])
def get_equalizer_presets():
    try:
        session = get_session()
        presets = EqualizerPresetRepository(session).get_all()
        result = [{
            'id': p.id,
            'name': p.name,
            'bands': p.bands,
            'preamp': p.preamp,
            'is_builtin': p.is_builtin
        } for p in presets]
        session.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get equalizer presets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equalizer/presets', methods=['POST'])
def create_equalizer_preset():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        bands = data.get('bands')
        preamp = float(data.get('preamp', 0.0))

        if not name:
            return jsonify({'error': 'Le nom est requis'}), 400
        if not isinstance(bands, list) or len(bands) != 10:
            return jsonify({'error': 'bands doit contenir exactement 10 valeurs'}), 400

        session = get_session()
        preset = EqualizerPresetRepository(session).create(name, [float(b) for b in bands], preamp)
        result = {'id': preset.id, 'name': preset.name, 'bands': preset.bands,
                   'preamp': preset.preamp, 'is_builtin': preset.is_builtin}
        session.close()
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Failed to create equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equalizer/presets/<preset_id>', methods=['PUT'])
def update_equalizer_preset(preset_id):
    try:
        data = request.json or {}
        name = data.get('name')
        bands = data.get('bands')
        preamp = data.get('preamp')

        if bands is not None and (not isinstance(bands, list) or len(bands) != 10):
            return jsonify({'error': 'bands doit contenir exactement 10 valeurs'}), 400

        session = get_session()
        repo = EqualizerPresetRepository(session)
        preset = repo.update(
            preset_id,
            name=name.strip() if name else None,
            bands=[float(b) for b in bands] if bands is not None else None,
            preamp=float(preamp) if preamp is not None else None
        )

        if not preset:
            session.close()
            return jsonify({'error': 'Preset introuvable ou en lecture seule'}), 404

        # Read everything off the ORM object before closing the session -
        # commit() (inside repo.update()) expires its attributes, so touching
        # them after close() raises a DetachedInstanceError.
        result = {'id': preset.id, 'name': preset.name, 'bands': preset.bands,
                  'preamp': preset.preamp, 'is_builtin': preset.is_builtin}
        session.close()

        # If this preset is the one currently active, re-apply it so the
        # edit takes effect immediately instead of on the next switch.
        if player_service.equalizer_preset_id == result['id']:
            player_service.set_equalizer_preset(result['id'], result['bands'], result['preamp'])

        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to update equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/equalizer/presets/<preset_id>', methods=['DELETE'])
def delete_equalizer_preset(preset_id):
    try:
        session = get_session()
        deleted = EqualizerPresetRepository(session).delete(preset_id)
        session.close()

        if not deleted:
            return jsonify({'error': 'Preset introuvable ou en lecture seule'}), 404

        # Deleted preset was active - fall back to disabled rather than
        # keep driving the live player off a preset that no longer exists.
        if player_service.equalizer_preset_id == preset_id:
            player_service.set_equalizer_preset(None)

        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/state', methods=['GET'])
def get_player_state():
    try:
        book = player_service.current_audiobook
        chapter_index = player_service.current_chapter_index
        chapter_title = None
        if book and book.chapters and 0 <= chapter_index < len(book.chapters):
            chapter_title = format_chapter_title(chapter_index, book.chapters[chapter_index].get('title'))

        state = {
            'is_playing': player_service.is_playing(),
            'is_paused': player_service.is_paused(),
            'position': player_service.get_current_position(),
            'duration': player_service.get_current_duration(),
            'volume': player_service.get_volume(),
            'speed': player_service.get_speed(),
            'equalizer_preset_id': player_service.equalizer_preset_id,
            'loudness_normalization_enabled': player_service.loudness_normalization_enabled,
            'compression_preset': player_service.compression_preset,
            'sleep_timer_remaining_seconds': player_service.get_sleep_timer_remaining_seconds(),
            'is_casting': player_service.is_casting(),
            'cast_device_name': player_service.get_cast_device_name(),
            'currentChapterIndex': chapter_index,
            'currentChapterTitle': chapter_title,
            'currentBook': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'narrator': book.narrator,
                'cover_url': book.cover,
                'description': book.description
            } if book else None
        }
        return jsonify(state)
    except Exception as e:
        logger.error(f"Failed to get player state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cast/devices', methods=['GET'])
def get_cast_devices():
    """Scan the local network for Chromecast/Google Home devices. Blocking
    for a few seconds - meant to be called from an explicit "scan" action."""
    try:
        devices = player_service.list_cast_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Failed to discover cast devices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cast/connect', methods=['POST'])
def connect_cast_device():
    try:
        data = request.json or {}
        device_name = data.get('device_name')
        if not device_name:
            return jsonify({'error': 'device_name requis'}), 400

        if not player_service.connect_cast_device(device_name):
            return jsonify({'error': 'Connexion au Chromecast échouée'}), 500

        return jsonify({'status': 'connected', 'device_name': device_name})
    except Exception as e:
        logger.error(f"Failed to connect cast device: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cast/disconnect', methods=['POST'])
def disconnect_cast_device():
    try:
        player_service.disconnect_cast_device()
        return jsonify({'status': 'disconnected'})
    except Exception as e:
        logger.error(f"Failed to disconnect cast device: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cast/local-audio', methods=['GET'])
def stream_local_audio_for_cast():
    """Streams an audio chapter over HTTP (with Range support) so a
    Chromecast, or the mobile app's native ExoPlayer, can fetch it without
    needing filesystem access or a source server's own auth token. Used
    internally by both CastPlayer (desktop) and mobilePlayerStore.ts
    (mobile), which always resolve this URL themselves from a chapter's
    real audio_file - that's a local filesystem path for local-folder
    books, or a remote Plex/Audiobookshelf streaming URL otherwise."""
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Fichier audio introuvable'}), 404

        if path.startswith('http://') or path.startswith('https://'):
            headers = {}
            if 'Range' in request.headers:
                headers['Range'] = request.headers['Range']
            upstream = requests.get(path, headers=headers, stream=True, timeout=15)
            excluded = {'content-encoding', 'transfer-encoding', 'connection'}
            response_headers = [
                (k, v) for k, v in upstream.headers.items() if k.lower() not in excluded
            ]
            return Response(
                upstream.iter_content(chunk_size=8192),
                status=upstream.status_code,
                headers=response_headers
            )

        AUDIO_EXTENSIONS = {'.mp3', '.m4b', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}
        file_path = Path(path)
        if file_path.suffix.lower() not in AUDIO_EXTENSIONS or not file_path.is_file():
            return jsonify({'error': 'Fichier audio introuvable'}), 404

        return send_file(str(file_path), conditional=True)
    except Exception as e:
        logger.error(f"Failed to stream local audio for cast: {e}")
        return jsonify({'error': str(e)}), 500

# Sync endpoints
@app.route('/api/sync', methods=['POST'])
def sync_servers():
    try:
        sync_service.sync_all_servers(background=True)
        return jsonify({'status': 'syncing'})
    except Exception as e:
        logger.error(f"Failed to sync: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    return jsonify({
        'syncing': sync_service.is_syncing(),
        'message': sync_service.get_last_message()
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/books/<book_id>/cover-proxy', methods=['GET'])
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
        return jsonify({'error': str(e)}), 500
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/local-cover/<book_id>', methods=['GET'])
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown_backend():
    """Best-effort cleanup called by Electron right before it force-kills this
    process on quit, so an in-progress reading session gets a final, accurate
    end time instead of relying solely on the periodic checkpoint."""
    try:
        player_service.stop()
    except Exception as e:
        logger.error(f"Failed to stop cleanly during shutdown: {e}")
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    logger.info("Starting Audook Backend...")
    init_database()

    seed_session = get_session()
    EqualizerPresetRepository(seed_session).ensure_builtins()
    seed_session.close()

    host = '0.0.0.0' if os.environ.get('AUDOOK_HEADLESS') == '1' else '127.0.0.1'
    app.run(host=host, port=5000, debug=False)
