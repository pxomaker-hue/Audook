"""System endpoints."""

from flask import Blueprint, jsonify, request

from app.api.context import services
from app.utils import logger

bp = Blueprint('system', __name__)


@bp.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@bp.route('/api/shutdown', methods=['POST'])
def shutdown_backend():
    """Best-effort cleanup called by Electron right before it force-kills this
    process on quit, so an in-progress reading session gets a final, accurate
    end time instead of relying solely on the periodic checkpoint."""
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify({'error': 'Forbidden'}), 403
    try:
        services.player.stop()
    except Exception as e:
        logger.error(f"Failed to stop cleanly during shutdown: {e}")
    return jsonify({'status': 'ok'})
