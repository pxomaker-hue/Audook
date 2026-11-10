"""Encryption at rest for stored server credentials (Plex token, Audiobookshelf
password).

The key comes from AUDOOK_SECRET_KEY (a Fernet key - best on a NAS, keeps it
off the data volume) or else a 0600 key file generated next to the database.
This protects against a leaked/backed-up database file; it cannot protect
against someone who already controls the account running Audook.
"""
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc:v1:"
_fernet = None


def _key_path() -> Path:
    return Path.home() / ".audook" / "secret.key"


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    key = os.environ.get("AUDOOK_SECRET_KEY", "").strip().encode()
    if not key:
        path = _key_path()
        if path.exists():
            key = path.read_bytes().strip()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
    _fernet = Fernet(key)
    return _fernet


def encrypt(value):
    if value is None or value == "" or value.startswith(PREFIX):
        return value
    return PREFIX + _get_fernet().encrypt(value.encode()).decode()


def decrypt(value):
    """Plaintext values (rows written before encryption existed) pass through."""
    if not value or not value.startswith(PREFIX):
        return value
    try:
        return _get_fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise ValueError("Cannot decrypt stored credential: wrong AUDOOK_SECRET_KEY / secret.key")


def reset_cache():
    global _fernet
    _fernet = None
