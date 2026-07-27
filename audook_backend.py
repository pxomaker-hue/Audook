#!/usr/bin/env python3
"""
Audook Backend - Exposes services via HTTP API for Electron frontend
"""

import sys
from pathlib import Path
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database, get_session, BookRepository, ReadingProgressRepository, ReadingHistoryRepository, ServerRepository, BookmarkRepository, EqualizerPresetRepository, AppSettingsRepository
from app.services import LibraryService, PlayerService, SyncService
from app.sync.scanner import scanner
from app.sync import progress_sync
from app.clients import PlexClient, AudiobookshelfClient
from app.local import LocalClient
from app.utils import logger, generate_id, online_metadata

app = Flask(__name__)
CORS(app)

# Initialize services
library_service = None
player_service = None
sync_service = None

# Health check endpoint for Electron app (before services init)
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

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
            password=password
        )

        return jsonify({
            'id': server.id,
            'type': server.type,
            'name': server.name,
            'url': server.url
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

        result = []
        for book in books:
            progress = in_progress.get(book.id)
            current_chapter_title = None
            if progress and book.chapters:
                chapter_index = progress.get('chapter_index') or 0
                if 0 <= chapter_index < len(book.chapters):
                    current_chapter_title = book.chapters[chapter_index].get('title')

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
            'author_bio': book.metadata.get('author_bio'),
            'author_photo': book.metadata.get('author_photo'),
            'manual_overrides': book.metadata.get('manual_overrides', []),
            'progress': {
                'position': progress.position_seconds,
                'percentage': progress.progress_percent
            },
            'is_finished': progress.is_finished,
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
        allowed_fields = ('title', 'author', 'narrator', 'description', 'cover_url', 'series')
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
        title = query or book.title
        author = None if query else book.author

        candidates = online_metadata.search_book_candidates(title, author)
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
        if not work_key:
            return jsonify({'error': 'work_key requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        details = online_metadata.get_book_work_details(work_key)
        fields = {}
        if details.get('description') and (mode == 'replace' or not book.description):
            fields['description'] = details['description']
        if details.get('cover_url') and (mode == 'replace' or not book.cover_url):
            fields['cover_url'] = details['cover_url']

        if not fields:
            return jsonify({'status': 'no_change'})

        book_repo.update_fields(book_id, fields, lock=True)
        return jsonify({'status': 'matched', 'applied': list(fields.keys())})
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

@app.route('/api/books/<book_id>/progress', methods=['DELETE'])
def delete_book_progress(book_id):
    """Reset a single book's reading progress (removes it from 'Reprendre l'écoute')"""
    try:
        session = get_session()
        deleted = ReadingProgressRepository(session).delete(book_id)
        if not deleted:
            return jsonify({'error': 'Aucune progression pour ce livre'}), 404
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

@app.route('/api/player/normalization', methods=['POST'])
def set_player_normalization():
    try:
        data = request.json or {}
        enabled = bool(data.get('enabled'))
        player_service.set_normalization(enabled)
        return jsonify({'status': 'normalization_set', 'enabled': enabled})
    except Exception as e:
        logger.error(f"Failed to set normalization: {e}")
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
        session.close()

        if not preset:
            return jsonify({'error': 'Preset introuvable ou en lecture seule'}), 404

        # If this preset is the one currently active, re-apply it so the
        # edit takes effect immediately instead of on the next switch.
        if player_service.equalizer_preset_id == preset.id:
            player_service.set_equalizer_preset(preset.id, preset.bands, preset.preamp)

        return jsonify({'id': preset.id, 'name': preset.name, 'bands': preset.bands,
                         'preamp': preset.preamp, 'is_builtin': preset.is_builtin})
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
            chapter_title = book.chapters[chapter_index].get('title')

        state = {
            'is_playing': player_service.is_playing(),
            'is_paused': player_service.is_paused(),
            'position': player_service.get_current_position(),
            'duration': player_service.get_current_duration(),
            'volume': player_service.get_volume(),
            'speed': player_service.get_speed(),
            'equalizer_preset_id': player_service.equalizer_preset_id,
            'normalization_enabled': player_service.normalization_enabled,
            'sleep_timer_remaining_seconds': player_service.get_sleep_timer_remaining_seconds(),
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

    app.run(host='127.0.0.1', port=5000, debug=False)
