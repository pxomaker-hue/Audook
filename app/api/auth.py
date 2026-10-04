"""Optional shared-secret authentication for the HTTP API.

Off by default (desktop: the backend only listens on 127.0.0.1). On a NAS,
set AUDOOK_API_TOKEN in the container environment and every request must then
carry the token, otherwise it gets a 401:

  - `Authorization: Bearer <token>` (what the app's axios calls send), or
  - `X-Audook-Token: <token>`, or
  - `?token=<token>` - ONLY on /api/cast/local-audio, which is fetched by
    things that can't set headers (ExoPlayer's media loader, a Chromecast).

Left public on purpose: /health (liveness probe the Electron shell waits on;
exposes nothing) and CORS preflight (OPTIONS) requests. /api/health is NOT
public, so the app can use it to check that its token is accepted.
"""
import hmac
import logging
import os
import re

from flask import jsonify, request

PUBLIC_PATHS = {'/health'}
QUERY_TOKEN_PATHS = {'/api/cast/local-audio'}


def configured_token() -> str:
    return os.environ.get('AUDOOK_API_TOKEN', '').strip()


def _provided_token() -> str:
    header = request.headers.get('Authorization', '')
    if header.lower().startswith('bearer '):
        return header[7:].strip()
    custom = request.headers.get('X-Audook-Token')
    if custom:
        return custom.strip()
    if request.path in QUERY_TOKEN_PATHS:
        return request.args.get('token', '').strip()
    return ''


def require_api_token():
    """Flask before_request hook: returns a 401 response, or None to continue."""
    expected = configured_token()
    if not expected:
        return None
    if request.method == 'OPTIONS' or request.path in PUBLIC_PATHS:
        return None
    if hmac.compare_digest(_provided_token().encode(), expected.encode()):
        return None
    return jsonify({'error': 'Unauthorized'}), 401


class _RedactTokenFilter(logging.Filter):
    """Werkzeug logs every request line, query string included - keep the
    ?token=... of media URLs out of the logs."""
    _pattern = re.compile(r'([?&]token=)[^&\s"]+')

    def filter(self, record):
        record.msg = self._pattern.sub(r'\1***', str(record.msg))
        if record.args:
            record.args = tuple(
                self._pattern.sub(r'\1***', a) if isinstance(a, str) else a for a in record.args
            )
        return True


def install_log_redaction():
    logging.getLogger('werkzeug').addFilter(_RedactTokenFilter())
