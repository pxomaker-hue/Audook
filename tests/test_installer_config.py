"""The NSIS installer must keep its custom "is the app running?" check:
electron-builder's stock one misses a single leftover process (e.g. an orphan
audook_backend.exe), so an update over a running/half-closed install ended up
half-installed and users had to uninstall first (see assets/installer.nsh)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _nsis_config():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["build"]["nsis"]


def test_installer_includes_the_custom_check():
    include = _nsis_config().get("include")
    assert include, "build.nsis.include must point to the custom NSIS hooks"
    assert (ROOT / include).is_file()


def test_custom_check_handles_a_single_leftover_process():
    script = (ROOT / _nsis_config()["include"]).read_text(encoding="utf-8")
    assert "!macro customCheckAppRunning" in script
    # robust against exactly one match (a bare `(...).Count` is empty for one object)
    assert "@(& $$f).Count" in script
    assert "Stop-Process" in script and "$INSTDIR" in script


def test_installer_hooks_are_plain_ascii():
    script = (ROOT / _nsis_config()["include"]).read_bytes()
    script.decode("ascii")  # NSIS may misread a BOM-less non-ASCII file
