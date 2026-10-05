"""Servers endpoints."""

import asyncio

from flask import Blueprint, jsonify, request

from app.api.errors import internal_error
from app.clients import AudiobookshelfClient, PlexClient
from app.database import ServerRepository, get_session
from app.local import LocalClient
from app.sync.scanner import scanner
from app.utils import generate_id, logger

bp = Blueprint('servers', __name__)


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


@bp.route('/api/servers', methods=['GET'])
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
        return internal_error()


@bp.route('/api/servers', methods=['POST'])
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
        return internal_error()


@bp.route('/api/servers/<server_id>', methods=['DELETE'])
def delete_server(server_id):
    try:
        session = get_session()
        server_repo = ServerRepository(session)
        server_repo.delete(server_id)
        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete server: {e}")
        return internal_error()


@bp.route('/api/servers/<server_id>/remote-access', methods=['POST'])
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
        return internal_error()


@bp.route('/api/servers/<server_id>/hidden', methods=['POST'])
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
        return internal_error()


@bp.route('/api/servers/<server_id>/test', methods=['POST'])
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
        return internal_error()


@bp.route('/api/servers/<server_id>/scan', methods=['POST'])
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
        return internal_error()
