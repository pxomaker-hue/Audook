"""Update endpoints (see app/utils/updater.py for the repository format)."""

import os
import subprocess
import sys

from flask import Blueprint, jsonify, request

import app
from app.utils import logger, updater

bp = Blueprint('updates', __name__)


def _headless():
    return os.environ.get('AUDOOK_HEADLESS') == '1'


@bp.route('/api/update/check', methods=['GET'])
def check_update():
    """?platform=windows|android (default: windows, or the NAS' own status when headless).
    ?current=x.y.z lets the Android app compare its own version, not the NAS'."""
    platform = request.args.get('platform') or 'windows'
    try:
        result = updater.check(platform, request.args.get('current') or None)
    except updater.UpdateError as e:
        message = str(e)  # our own French messages, never a raw library exception
        return jsonify({'error': message, 'current': app.__version__}), 502
    # A container can't replace itself: the NAS image is rebuilt by hand.
    result['selfUpdate'] = platform == 'android' or (platform == 'windows' and not _headless())
    return jsonify(result)


@bp.route('/api/update/install', methods=['POST'])
def install_update():
    """Windows desktop only: download + verify the installer, then launch it.
    The caller (Electron UI) quits the app right after."""
    if (request.remote_addr not in ('127.0.0.1', '::1') or request.headers.get('X-Forwarded-For')
            or _headless() or sys.platform != 'win32'):
        return jsonify({'error': 'Forbidden'}), 403
    try:
        info = updater.check('windows')
        if not info['available']:
            return jsonify({'error': 'Aucune mise à jour disponible'}), 409
        path = updater.download(info['asset'])
    except updater.UpdateError as e:
        message = str(e)
        logger.error(f'Update failed: {message}')
        return jsonify({'error': message}), 502
    subprocess.Popen([path], close_fds=True, creationflags=0x00000008)  # DETACHED_PROCESS
    return jsonify({'status': 'launched', 'version': info['latest']})
