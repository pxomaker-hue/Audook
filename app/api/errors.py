"""Error responses that don't leak internals.

Routes used to answer 500 with the raw exception text in the body, which hands
the client internals (file paths, SQL, upstream URLs, library details). The full
detail now goes to the log (with traceback) and the client gets a generic message.
"""
from flask import jsonify, request

from app.utils import logger

GENERIC_MESSAGE = 'Erreur interne du serveur'


def internal_error():
    """Call from inside an `except` block: logs the traceback, returns the 500 response."""
    logger.exception('Unhandled error in %s %s', request.method, request.path)
    return jsonify({'error': GENERIC_MESSAGE}), 500
