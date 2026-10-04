"""package.json is the single source of truth for the version: the backend's
__version__ must match it (scripts/sync-version.js keeps them aligned), and the
Android build must derive its versionCode from it."""
import json
import re
from pathlib import Path

import app

ROOT = Path(__file__).resolve().parent.parent


def _package_version():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def test_backend_version_matches_package_json():
    assert app.__version__ == _package_version(), "run: node scripts/sync-version.js"


def test_package_version_is_plain_semver_that_fits_the_android_version_code():
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", _package_version())
    assert match, "use MAJOR.MINOR.PATCH"
    _, minor, patch = map(int, match.groups())
    assert minor < 100 and patch < 100


def test_gradle_derives_its_version_from_package_json():
    gradle = (ROOT / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    assert "package.json" in gradle
    assert re.search(r"versionCode\s+appVersionCode", gradle)
    assert re.search(r"versionName\s+appVersionName", gradle)
    # no leftover hardcoded numbers
    assert not re.search(r"versionCode\s+\d", gradle)
    assert not re.search(r'versionName\s+"', gradle)
