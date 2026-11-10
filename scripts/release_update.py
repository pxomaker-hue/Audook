#!/usr/bin/env python3
"""Release helper for the update repository (see app/utils/updater.py).

  python scripts/release_update.py keygen
      One-off: creates release-signing.key (PRIVATE, gitignored - back it up, never share it)
      and writes the matching public key into app/update_key.py. Rebuild the app
      afterwards so it embeds that key.

  python scripts/release_update.py manifest [--notes-file CHANGELOG-1.0.4.txt]
      Reads release/Audook-Setup-<v>.exe and release/Audook-<v>.apk (whichever exist),
      writes release/latest.json and release/latest.json.sig. Upload the installers and
      these two files to the update repository.
"""
import argparse
import base64
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / 'release-signing.key'
PUBKEY_PY = ROOT / 'app' / 'update_key.py'
RAW = serialization.Encoding.Raw


def keygen():
    if KEY_FILE.exists():
        sys.exit(f'{KEY_FILE.name} existe déjà : refus de l\'écraser.')
    key = Ed25519PrivateKey.generate()
    KEY_FILE.write_text(base64.b64encode(
        key.private_bytes(RAW, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode())
    pub = base64.b64encode(key.public_key().public_bytes(RAW, serialization.PublicFormat.Raw)).decode()
    src = PUBKEY_PY.read_text(encoding='utf-8')
    PUBKEY_PY.write_text(re.sub(r'^UPDATE_PUBLIC_KEY = ".*"', f'UPDATE_PUBLIC_KEY = "{pub}"', src, flags=re.M),
                         encoding='utf-8')
    print(f'Clé privée : {KEY_FILE} (à sauvegarder, ne jamais la partager)\nClé publique : {pub}')


def manifest(notes_file):
    version = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
    release = ROOT / 'release'
    platforms = {}
    for name, filename in (('windows', f'Audook-Setup-{version}.exe'), ('android', f'Audook-{version}.apk')):
        path = release / filename
        if path.exists():
            platforms[name] = {'file': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                               'size': path.stat().st_size}
    if not platforms:
        sys.exit(f'Aucun fichier Audook-*-{version} dans {release}')
    notes = Path(notes_file).read_text(encoding='utf-8').strip() if notes_file else ''
    data = json.dumps({'version': version, 'released': datetime.date.today().isoformat(),
                       'notes': notes, 'platforms': platforms}, indent=2, ensure_ascii=False).encode('utf-8')
    if not KEY_FILE.exists():
        sys.exit('release-signing.key introuvable : lancez d\'abord `keygen`.')
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(KEY_FILE.read_text().strip()))
    (release / 'latest.json').write_bytes(data)
    (release / 'latest.json.sig').write_text(base64.b64encode(key.sign(data)).decode())
    print(f'release/latest.json + latest.json.sig écrits ({", ".join(platforms)}) pour {version}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('keygen')
    m = sub.add_parser('manifest')
    m.add_argument('--notes-file')
    args = parser.parse_args()
    keygen() if args.cmd == 'keygen' else manifest(args.notes_file)
