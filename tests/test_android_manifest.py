"""Android manifest guard rails."""
import re
from pathlib import Path

MANIFEST = (Path(__file__).resolve().parent.parent / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")


def test_app_data_is_not_backed_up():
    # local storage holds the server address and the API token
    assert re.search(r'android:allowBackup="false"', MANIFEST)


def test_cleartext_http_stays_enabled_for_the_lan_backend():
    # the NAS is plain http on a LAN IP chosen by the user - Android's network
    # security config can't allow "private ranges only", so this must stay on
    assert re.search(r'android:usesCleartextTraffic="true"', MANIFEST)
