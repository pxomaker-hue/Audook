import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import app
from app.utils import updater


def _keys():
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    return key, pub


def _signed(key, **over):
    manifest = {"version": "9.9.9", "notes": "n", "platforms": {
        "windows": {"file": "Audook-Setup-9.9.9.exe", "sha256": "a" * 64, "size": 3}}}
    manifest.update(over)
    raw = json.dumps(manifest).encode()
    return raw, base64.b64encode(key.sign(raw)).decode()


def test_valid_signature_accepted_tampered_rejected():
    key, pub = _keys()
    raw, sig = _signed(key)
    assert updater.verify_manifest(raw, sig, pub)["version"] == "9.9.9"
    with pytest.raises(updater.UpdateError):
        updater.verify_manifest(raw.replace(b"9.9.9", b"9.9.8"), sig, pub)
    with pytest.raises(updater.UpdateError):
        updater.verify_manifest(raw, sig, _keys()[1])


def test_unconfigured_key_refuses_everything():
    key, _ = _keys()
    raw, sig = _signed(key)
    with pytest.raises(updater.UpdateError):
        updater.verify_manifest(raw, sig, "")


def _patch_manifest(monkeypatch, **over):
    key, pub = _keys()
    raw, sig = _signed(key, **over)
    monkeypatch.setattr(updater, "fetch_manifest", lambda: updater.verify_manifest(raw, sig, pub))


def test_check_reports_newer_version_only(monkeypatch):
    _patch_manifest(monkeypatch)
    assert updater.check("windows", "1.0.3")["available"] is True
    assert updater.check("windows", "9.9.9")["available"] is False
    assert updater.check("windows", "10.0.0")["available"] is False  # never a downgrade
    assert updater.check("android", "1.0.3")["available"] is False   # no android asset


def test_manifest_with_path_traversal_file_rejected(monkeypatch):
    _patch_manifest(monkeypatch, platforms={"windows": {"file": "../evil.exe", "sha256": "a" * 64, "size": 3}})
    with pytest.raises(updater.UpdateError):
        updater.check("windows", "1.0.3")


class _Resp:
    def __init__(self, data):
        self.data = data
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def raise_for_status(self): pass
    def iter_content(self, n): yield self.data


def test_download_checks_sha256_and_size(monkeypatch, tmp_path):
    data = b"installer"
    asset = {"file": "a.exe", "url": "https://x/a.exe", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    monkeypatch.setattr(updater.requests, "get", lambda *a, **k: _Resp(data))
    assert open(updater.download(asset, str(tmp_path)), "rb").read() == data
    monkeypatch.setattr(updater.requests, "get", lambda *a, **k: _Resp(b"tampered!"))
    with pytest.raises(updater.UpdateError):
        updater.download(asset, str(tmp_path))
    assert not (tmp_path / "a.exe").exists()


def test_version_constant_still_semver():
    assert updater.parse_version(app.__version__)


def test_check_endpoint_reports_failure_as_502(client, monkeypatch):
    def boom(*a, **k):
        raise updater.requests.ConnectionError("offline")
    monkeypatch.setattr(updater.requests, "get", boom)
    response = client.get("/api/update/check?platform=windows")
    assert response.status_code == 502 and "error" in response.get_json()


def test_install_endpoint_is_loopback_only(client):
    assert client.post("/api/update/install", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 403
