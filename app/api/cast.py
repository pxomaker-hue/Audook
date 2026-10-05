"""Cast endpoints."""

from pathlib import Path

import requests
from flask import Blueprint, Response, jsonify, request, send_file

from app import DATA_DIR
from app.api.context import services
from app.api.errors import internal_error
from app.database import ServerRepository, get_session
from app.utils import logger

bp = Blueprint('cast', __name__)


@bp.route('/api/cast/devices', methods=['GET'])
def get_cast_devices():
    """Scan the local network for Chromecast/Google Home devices. Blocking
    for a few seconds - meant to be called from an explicit "scan" action."""
    try:
        devices = services.player.list_cast_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Failed to discover cast devices: {e}")
        return internal_error()

@bp.route('/api/cast/connect', methods=['POST'])
def connect_cast_device():
    try:
        data = request.json or {}
        device_name = data.get('device_name')
        if not device_name:
            return jsonify({'error': 'device_name requis'}), 400

        if not services.player.connect_cast_device(device_name):
            return jsonify({'error': 'Connexion au Chromecast échouée'}), 500

        return jsonify({'status': 'connected', 'device_name': device_name})
    except Exception as e:
        logger.error(f"Failed to connect cast device: {e}")
        return internal_error()

@bp.route('/api/cast/disconnect', methods=['POST'])
def disconnect_cast_device():
    try:
        services.player.disconnect_cast_device()
        return jsonify({'status': 'disconnected'})
    except Exception as e:
        logger.error(f"Failed to disconnect cast device: {e}")
        return internal_error()


def _allowed_audio_sources():
    """Hosts and folders /api/cast/local-audio is allowed to serve from: only
    what the user configured as a server (Plex/Audiobookshelf hosts, local
    library folders) plus Audook's own data dir (cleaned audio copies).
    Without this the endpoint was an open proxy (any URL) and an arbitrary
    audio-file reader (any path on the machine)."""
    from urllib.parse import urlparse
    hosts, roots = set(), [DATA_DIR.resolve()]
    session = get_session()
    for server in ServerRepository(session).get_all():
        if server.type == 'local':
            if server.url:
                roots.append(Path(server.url).resolve())
            continue
        for candidate in (server.url, server.remote_url):
            if candidate:
                host = urlparse(candidate if '://' in candidate else f'http://{candidate}').netloc.lower()
                if host:
                    hosts.add(host)
    return hosts, roots

@bp.route('/api/cast/local-audio', methods=['GET'])
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

        allowed_hosts, allowed_roots = _allowed_audio_sources()

        if path.startswith('http://') or path.startswith('https://'):
            from urllib.parse import urlparse
            if urlparse(path).netloc.lower() not in allowed_hosts:
                return jsonify({'error': 'Source non autorisée'}), 403
            headers = {}
            if 'Range' in request.headers:
                headers['Range'] = request.headers['Range']
            upstream = requests.get(path, headers=headers, stream=True, timeout=15, allow_redirects=False)
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
        file_path = Path(path).resolve()
        if file_path.suffix.lower() not in AUDIO_EXTENSIONS or not file_path.is_file():
            return jsonify({'error': 'Fichier audio introuvable'}), 404
        if not any(root == file_path or root in file_path.parents for root in allowed_roots):
            return jsonify({'error': 'Source non autorisée'}), 403

        return send_file(str(file_path), conditional=True)
    except Exception as e:
        logger.error(f"Failed to stream local audio for cast: {e}")
        return internal_error()
