"""Helpers shared by the endpoints that fetch remote media on the client's
behalf (cover proxy, cast/local audio): which hosts/folders are allowed, SSRF
checks, and upstream-token handling.

Upstream tokens (Plex ``X-Plex-Token``, Audiobookshelf ``token``) are stored in
the library URLs but must never reach API clients: ``strip_secret_params``
removes them from responses, and ``with_server_token`` puts them back
server-side when the backend itself fetches the media.
"""
import ipaddress
import socket
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app import DATA_DIR
from app.database import ServerRepository, get_session

SECRET_PARAMS = {'token', 'x-plex-token'}
MAX_COVER_BYTES = 10 * 1024 * 1024
_abs_tokens = {}


def strip_secret_params(url):
    """Remove upstream credentials from a URL before it is sent to a client."""
    if not url or not isinstance(url, str) or '?' not in url:
        return url
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in SECRET_PARAMS]
    return urlunparse(parts._replace(query=urlencode(query)))


def redact_chapters(chapters):
    return [{**c, 'audio_file': strip_secret_params(c.get('audio_file'))} if isinstance(c, dict) else c
            for c in chapters or []]


def _host(url):
    return urlparse(url if '://' in url else f'http://{url}').netloc.lower()


def configured_sources():
    """(servers by host, allowed local roots) - from the user's configured servers."""
    hosts, roots = {}, [DATA_DIR.resolve()]
    for server in ServerRepository(get_session()).get_all():
        if server.type == 'local':
            if server.url:
                roots.append(Path(server.url).resolve())
            continue
        for candidate in (server.url, server.remote_url):
            if candidate and _host(candidate):
                hosts[_host(candidate)] = server
    return hosts, roots


def is_public_address(host):
    """False for loopback/private/link-local/reserved targets (SSRF guard)."""
    name = host.rsplit('@', 1)[-1]
    name = name.rsplit(':', 1)[0] if not name.endswith(']') else name
    name = name.strip('[]')
    try:
        infos = socket.getaddrinfo(name, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split('%')[0])
        if not ip.is_global:
            return False
    return bool(infos)


def with_server_token(url, server):
    """Re-add the upstream credential that strip_secret_params removed."""
    if any(k.lower() in SECRET_PARAMS for k, _ in parse_qsl(urlparse(url).query)):
        return url
    token = None
    if server.type == 'plex':
        param, token = 'X-Plex-Token', server.api_key
    elif server.type == 'audiobookshelf':
        param = 'token'
        token = _abs_tokens.get(server.id)
        if not token:
            from app.clients import AudiobookshelfClient
            try:
                token = AudiobookshelfClient(server.url, server.username, server.password).auth_token
            except Exception:
                return url
            _abs_tokens[server.id] = token
    if not token:
        return url
    parts = urlparse(url)
    return urlunparse(parts._replace(query=urlencode(parse_qsl(parts.query) + [(param, token)])))


def has_secret_param(url):
    return isinstance(url, str) and any(
        k.lower() in SECRET_PARAMS for k, _ in parse_qsl(urlparse(url).query))


def public_cover_url(book_id, url):
    """Cover URL safe to hand to a client: a URL carrying an upstream token is
    replaced by this backend's own cover-proxy endpoint."""
    if has_secret_param(url):
        from flask import request
        return f"{request.host_url.rstrip('/')}/api/books/{book_id}/cover-proxy"
    return url


def public_photo_url(book_id, url):
    if has_secret_param(url):
        from flask import request
        return f"{request.host_url.rstrip('/')}/api/books/{book_id}/author-photo-proxy"
    return url
