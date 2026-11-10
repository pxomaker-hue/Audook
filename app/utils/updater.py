"""Update check / download for Audook.

The update repository (AUDOOK_UPDATE_URL, default below) is a plain static folder:

    latest.json       {"version", "released", "notes", "platforms": {"windows": {...}, "android": {...}}}
    latest.json.sig   base64 Ed25519 signature of the exact bytes of latest.json
    <files>           installers listed in the manifest ({"file", "sha256", "size"})

The manifest is only trusted if its signature verifies against app.update_key.UPDATE_PUBLIC_KEY;
a downloaded file is only trusted if its SHA-256 and size match the signed manifest.
"""

import base64
import hashlib
import json
import os
import re
import tempfile

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import app
from app import update_key

DEFAULT_UPDATE_URL = 'https://easywork.kairos-app.website/audook/'
MAX_MANIFEST_BYTES = 256 * 1024
PLATFORMS = ('windows', 'android')
_FILE_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
_VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')


class UpdateError(Exception):
    pass


def base_url():
    url = os.environ.get('AUDOOK_UPDATE_URL', DEFAULT_UPDATE_URL).strip()
    return url if url.endswith('/') else url + '/'


def parse_version(value):
    if not isinstance(value, str) or not _VERSION_RE.match(value):
        raise UpdateError(f'Version invalide : {value!r}')
    return tuple(int(p) for p in value.split('.'))


def verify_manifest(raw, signature_b64, public_key_b64=None):
    """Return the parsed manifest if `raw` is validly signed, else raise UpdateError."""
    key = public_key_b64 if public_key_b64 is not None else update_key.UPDATE_PUBLIC_KEY
    if not key:
        raise UpdateError("Clé de signature des mises à jour non configurée")
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(
            base64.b64decode(signature_b64.strip()), raw)
    except (InvalidSignature, ValueError):
        raise UpdateError('Signature du manifeste invalide')
    try:
        manifest = json.loads(raw)
    except ValueError:
        raise UpdateError('Manifeste illisible')
    parse_version(manifest.get('version'))
    return manifest


def _get(url, max_bytes):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise UpdateError(f'Dépôt de mises à jour injoignable : {e}')
    if len(resp.content) > max_bytes:
        raise UpdateError('Réponse trop volumineuse')
    return resp.content


def fetch_manifest():
    raw = _get(base_url() + 'latest.json', MAX_MANIFEST_BYTES)
    sig = _get(base_url() + 'latest.json.sig', 1024).decode('ascii', 'ignore')
    return verify_manifest(raw, sig)


def _asset(manifest, platform):
    entry = (manifest.get('platforms') or {}).get(platform)
    if not entry:
        return None
    name, sha, size = entry.get('file'), entry.get('sha256'), entry.get('size')
    if (not isinstance(name, str) or not _FILE_RE.match(name)
            or not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha)
            or not isinstance(size, int) or size <= 0):
        raise UpdateError(f'Entrée {platform} invalide dans le manifeste')
    return {'file': name, 'sha256': sha, 'size': size, 'url': base_url() + name}


def check(platform, current=None):
    """Compare the signed manifest to `current` (default: this backend's version)."""
    if platform not in PLATFORMS:
        raise UpdateError('Plateforme inconnue')
    current = current or app.__version__
    manifest = fetch_manifest()
    latest = manifest['version']
    available = parse_version(latest) > parse_version(current)
    asset = _asset(manifest, platform)
    return {
        'current': current,
        'latest': latest,
        'available': bool(available and asset),
        'notes': str(manifest.get('notes') or '')[:4000],
        'released': manifest.get('released'),
        'asset': asset if available else None,
    }


def download(asset, dest_dir=None):
    """Download `asset` (from check()) and verify size + SHA-256. Returns the file path."""
    dest_dir = dest_dir or tempfile.mkdtemp(prefix='audook-update-')
    path = os.path.join(dest_dir, asset['file'])
    digest = hashlib.sha256()
    total = 0
    try:
        with requests.get(asset['url'], stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(path, 'wb') as out:
                for chunk in resp.iter_content(1024 * 256):
                    total += len(chunk)
                    if total > asset['size']:
                        raise UpdateError('Fichier plus gros que prévu')
                    digest.update(chunk)
                    out.write(chunk)
    except requests.RequestException as e:
        raise UpdateError(f'Téléchargement impossible : {e}')
    except UpdateError:
        os.remove(path)
        raise
    if total != asset['size'] or digest.hexdigest() != asset['sha256']:
        os.remove(path)
        raise UpdateError("Intégrité du fichier téléchargé non vérifiée (SHA-256)")
    return path
