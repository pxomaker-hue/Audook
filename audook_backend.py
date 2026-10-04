#!/usr/bin/env python3
"""
Audook Backend - Exposes services via HTTP API for Electron frontend

Routes live in app/api/ (one Flask blueprint per area); this file only wires
the app together: CORS, lazy service initialisation, DB session teardown and
the blueprint registration.
"""

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.api import register_blueprints
from app.api.context import services
from app.database import init_database, get_session, remove_session, EqualizerPresetRepository
from app.services import LibraryService, PlayerService, SyncService
from app.utils import logger

app = Flask(__name__)
CORS(app)


# Health check endpoint for Electron app (before services init)
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.teardown_appcontext
def cleanup_db_session(exception=None):
    # Almost none of the routes call session.close() themselves - this
    # returns the connection to the pool at the end of every request instead
    # of leaking it, which otherwise exhausts SQLAlchemy's default pool
    # (size 5 + 10 overflow) within seconds under mobile's frequent polling.
    remove_session()

@app.before_request
def init_services():
    # Skip for health check endpoint
    if request.path == '/health':
        return

    if services.library is None:
        try:
            services.library = LibraryService()
            services.player = PlayerService()
            services.sync = SyncService()
            services.player.restore_audio_settings()
            # Auto-sync once on startup so "Reprendre l'écoute" reflects
            # progress made elsewhere (mobile, ABS/Plex web player) without
            # needing to remember to hit "Synchroniser" first - runs in the
            # background (same call the manual sync button uses), so it
            # never delays the app becoming usable.
            services.sync.sync_all_servers(background=True)
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            # Continue anyway - services will be retried on next request
            pass


register_blueprints(app)

if __name__ == '__main__':
    logger.info("Starting Audook Backend...")
    init_database()

    seed_session = get_session()
    EqualizerPresetRepository(seed_session).ensure_builtins()
    seed_session.close()

    host = '0.0.0.0' if os.environ.get('AUDOOK_HEADLESS') == '1' else '127.0.0.1'
    app.run(host=host, port=5000, debug=False)
