"""Sync endpoints."""

from flask import Blueprint, jsonify

from app.api.context import services
from app.api.errors import internal_error
from app.utils import logger

bp = Blueprint('sync', __name__)


# Sync endpoints
@bp.route('/api/sync', methods=['POST'])
def sync_servers():
    try:
        services.sync.sync_all_servers(background=True)
        return jsonify({'status': 'syncing'})
    except Exception as e:
        logger.error(f"Failed to sync: {e}")
        return internal_error()

@bp.route('/api/sync/status', methods=['GET'])
def sync_status():
    return jsonify({
        'syncing': services.sync.is_syncing(),
        'message': services.sync.get_last_message()
    })
