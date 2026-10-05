"""The NSIS installer must keep its custom "is the app running?" check:
electron-builder's stock one misses a single leftover process (e.g. an orphan
audook_backend.exe), so an update over a running/half-closed install ended up
half-installed and users had to uninstall first (see assets/installer.nsh)."""
import codecs
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


def test_installer_hooks_with_accents_are_utf8_with_bom():
    # NSIS reads a BOM-less non-ASCII script as ANSI and garbles the accents
    raw = (ROOT / _nsis_config()["include"]).read_bytes()
    assert raw.startswith(codecs.BOM_UTF8)
    raw.decode("utf-8-sig")


def test_installer_branding_files_exist_and_have_the_nsis_sizes():
    from PIL import Image  # Pillow is only needed by the asset generator and this test
    nsis = _nsis_config()
    sizes = {"installerSidebar": (164, 314), "uninstallerSidebar": (164, 314), "installerHeader": (150, 57)}
    for key, expected in sizes.items():
        path = ROOT / nsis[key]
        assert path.is_file(), key
        with Image.open(path) as image:
            assert image.format == "BMP" and image.size == expected, (key, image.size)
    for key in ("installerIcon", "uninstallerIcon"):
        assert (ROOT / nsis[key]).is_file(), key


def test_installer_is_french_and_named_audook():
    nsis = _nsis_config()
    assert nsis["language"] == "1036" and nsis["installerLanguages"] == ["fr_FR"]
    assert nsis["shortcutName"] == "Audook" and nsis["artifactName"].startswith("Audook-Setup-")
    script = (ROOT / nsis["include"]).read_text(encoding="utf-8-sig")
    assert "!macro customWelcomePage" in script and "MUI_PAGE_WELCOME" in script


def test_installer_does_not_depend_on_the_old_versions_uninstaller():
    # The old uninstaller moves every file to %TEMP% and aborts if ONE is held open (by a
    # process outside the install folder: antivirus, backup tool...), which blocked updates
    # at ~25% with "cannot be closed" even with no Audook process left. The installer skips
    # it by clearing the UninstallString it would run; the uninstaller build must keep it.
    script = (ROOT / _nsis_config()["include"]).read_text(encoding="utf-8")
    assert 'DeleteRegValue SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "UninstallString"' in script
    assert 'DeleteRegValue HKEY_CURRENT_USER "${UNINSTALL_REGISTRY_KEY}" "UninstallString"' in script
    guarded = script.split("!ifndef BUILD_UNINSTALLER", 1)[1]
    assert "DeleteRegValue" in guarded.split("!endif")[0] + guarded.split("!endif")[1]


def test_packaged_app_only_ships_what_the_electron_main_process_needs():
    # The React app is bundled into build/ by CRA, so react/axios/Capacitor... are build-time
    # only. Shipping all of node_modules put ~700 Gradle build artifacts of @capacitor/android
    # in the installer, with paths > 259 characters: extraction failed at ~25% with a bogus
    # "cannot be closed" dialog. Keep them out of `dependencies`.
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert set(package["dependencies"]) == {"electron-is-dev"}, "front-end libs belong in devDependencies"
    assert not [f for f in package["build"]["files"] if f.startswith("node_modules")]
    main = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")
    third_party = {m for m in __import__("re").findall(r"require\(['\"]([^'\"]+)['\"]\)", main)
                   if not m.startswith(".") and m not in {"electron", "path", "fs", "child_process", "os", "http", "https", "net", "url"}}
    assert third_party <= set(package["dependencies"]), f"main.js needs {third_party} at runtime"
