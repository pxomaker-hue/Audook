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

from app.database import init_database, get_session, BookRepository, ReadingProgressRepository, ReadingHistoryRepository, ServerRepository
from app.services import LibraryService, PlayerService, SyncService
from app.sync.scanner import scanner
from app.clients import PlexClient, AudiobookshelfClient
from app.local import LocalClient
from app.utils import logger, generate_id

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
        in_progress = ReadingProgressRepository(session).get_in_progress_map()
        return jsonify([{
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover,
            'duration': book.duration,
            'description': book.description,
            'source': book.source,
            'progress_percent': in_progress.get(book.id, 0),
            'author_bio': book.metadata.get('author_bio'),
            'author_photo': book.metadata.get('author_photo')
        } for book in books])
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

        return jsonify({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover,
            'duration': book.duration,
            'description': book.description,
            'chapters': book.chapters,
            'progress': {
                'position': progress.position_seconds,
                'percentage': progress.progress_percent
            }
        })
    except Exception as e:
        logger.error(f"Failed to get book details: {e}")
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

if __name__ == '__main__':
    logger.info("Starting Audook Backend...")
    init_database()
    app.run(host='127.0.0.1', port=5000, debug=False)
