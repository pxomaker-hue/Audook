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
from werkzeug.exceptions import HTTPException

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.api import register_blueprints
from app.api.auth import install_log_redaction, require_api_token
from app.api.errors import internal_error
from app.api.context import services
from app.database import init_database, get_session, remove_session, EqualizerPresetRepository
from app.services import LibraryService, PlayerService, SyncService
from app.utils import logger

app = Flask(__name__)
CORS(app)
install_log_redaction()


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

# Registered before init_services so an unauthenticated request is rejected
# without triggering the (heavy) lazy service initialisation.
app.before_request(require_api_token)

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


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    # Anything a route didn't catch itself: generic JSON 500 (details go to the
    # log), instead of Flask's HTML page. HTTP errors (404, 405...) pass through.
    if isinstance(error, HTTPException):
        return error
    return internal_error()

if __name__ == '__main__':
    logger.info("Starting Audook Backend...")
    init_database()

    seed_session = get_session()
    EqualizerPresetRepository(seed_session).ensure_builtins()
    seed_session.close()

    host = '0.0.0.0' if os.environ.get('AUDOOK_HEADLESS') == '1' else '127.0.0.1'
    # AUDOOK_PORT only exists for tests / unusual setups: the apps expect 5000.
    app.run(host=host, port=int(os.environ.get('AUDOOK_PORT', '5000')), debug=False)
