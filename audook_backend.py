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

from app.database import init_database, get_session, BookRepository, ReadingProgressRepository
from app.services import LibraryService, PlayerService, SyncService
from app.utils import logger

app = Flask(__name__)
CORS(app)

# Initialize services
library_service = None
player_service = None
sync_service = None

@app.before_request
def init_services():
    global library_service, player_service, sync_service
    if library_service is None:
        session = get_session()
        library_service = LibraryService(session)
        player_service = PlayerService(session)
        sync_service = SyncService(session)

# Library endpoints
@app.route('/api/books', methods=['GET'])
def get_books():
    try:
        books = library_service.get_all_books()
        return jsonify([{
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover_url,
            'duration': book.duration,
            'description': book.description
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
        progress = progress_repo.get_by_book_id(book_id)

        return jsonify({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover_url,
            'duration': book.duration,
            'description': book.description,
            'chapters': [ch.to_dict() for ch in book.chapters],
            'progress': {
                'position': progress.position if progress else 0,
                'percentage': (progress.position / book.duration * 100) if progress and book.duration else 0
            } if progress else {'position': 0, 'percentage': 0}
        })
    except Exception as e:
        logger.error(f"Failed to get book details: {e}")
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
            'cover_url': book.cover_url
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
        player_service.play(book_id)
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
        state = player_service.get_state()
        return jsonify(state)
    except Exception as e:
        logger.error(f"Failed to get player state: {e}")
        return jsonify({'error': str(e)}), 500

# Sync endpoints
@app.route('/api/sync', methods=['POST'])
def sync_servers():
    try:
        sync_service.sync_all()
        return jsonify({'status': 'syncing'})
    except Exception as e:
        logger.error(f"Failed to sync: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    logger.info("Starting Audook Backend...")
    init_database()
    app.run(host='127.0.0.1', port=5000, debug=False)
