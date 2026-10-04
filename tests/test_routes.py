"""Guards the HTTP surface: the frontends (Electron, Android) hard-code these
paths, so a refactor that drops or renames a route must fail loudly here."""

EXPECTED_ROUTES = [
    ('/api/authors/<name>', 'PATCH'),
    ('/api/authors/<name>/refresh', 'POST'),
    ('/api/bookmarks/<int:bookmark_id>', 'DELETE'),
    ('/api/bookmarks/<int:bookmark_id>/resume', 'POST'),
    ('/api/books', 'GET'),
    ('/api/books/<book_id>', 'GET'),
    ('/api/books/<book_id>', 'PATCH'),
    ('/api/books/<book_id>/bookmarks', 'POST'),
    ('/api/books/<book_id>/clean-audio', 'POST'),
    ('/api/books/<book_id>/cover-proxy', 'GET'),
    ('/api/books/<book_id>/finished', 'POST'),
    ('/api/books/<book_id>/lock', 'POST'),
    ('/api/books/<book_id>/loudness-gain', 'GET'),
    ('/api/books/<book_id>/match', 'POST'),
    ('/api/books/<book_id>/match-candidates', 'GET'),
    ('/api/books/<book_id>/progress', 'DELETE'),
    ('/api/books/<book_id>/progress', 'POST'),
    ('/api/books/<book_id>/unlock', 'POST'),
    ('/api/books/<book_id>/use-cleaned-audio', 'POST'),
    ('/api/books/search', 'GET'),
    ('/api/cast/connect', 'POST'),
    ('/api/cast/devices', 'GET'),
    ('/api/cast/disconnect', 'POST'),
    ('/api/cast/local-audio', 'GET'),
    ('/api/collections', 'GET'),
    ('/api/collections', 'POST'),
    ('/api/collections/<collection_id>', 'DELETE'),
    ('/api/collections/<collection_id>', 'PATCH'),
    ('/api/collections/<collection_id>/books', 'POST'),
    ('/api/collections/<collection_id>/books/<book_id>', 'DELETE'),
    ('/api/equalizer/presets', 'GET'),
    ('/api/equalizer/presets', 'POST'),
    ('/api/equalizer/presets/<preset_id>', 'DELETE'),
    ('/api/equalizer/presets/<preset_id>', 'PUT'),
    ('/api/health', 'GET'),
    ('/api/history', 'DELETE'),
    ('/api/history', 'GET'),
    ('/api/history/<int:session_id>', 'DELETE'),
    ('/api/local-cover/<book_id>', 'GET'),
    ('/api/player/compression/cycle', 'POST'),
    ('/api/player/equalizer', 'POST'),
    ('/api/player/equalizer/cycle', 'POST'),
    ('/api/player/loudness-normalization', 'POST'),
    ('/api/player/next-chapter', 'POST'),
    ('/api/player/pause', 'POST'),
    ('/api/player/play', 'POST'),
    ('/api/player/previous-chapter', 'POST'),
    ('/api/player/resume', 'POST'),
    ('/api/player/seek', 'POST'),
    ('/api/player/sleep-timer', 'POST'),
    ('/api/player/speed', 'POST'),
    ('/api/player/state', 'GET'),
    ('/api/player/stop', 'POST'),
    ('/api/player/volume', 'POST'),
    ('/api/progress', 'DELETE'),
    ('/api/progress/dismissed-flags', 'DELETE'),
    ('/api/servers', 'GET'),
    ('/api/servers', 'POST'),
    ('/api/servers/<server_id>', 'DELETE'),
    ('/api/servers/<server_id>/hidden', 'POST'),
    ('/api/servers/<server_id>/remote-access', 'POST'),
    ('/api/servers/<server_id>/scan', 'POST'),
    ('/api/servers/<server_id>/test', 'POST'),
    ('/api/shutdown', 'POST'),
    ('/api/sync', 'POST'),
    ('/api/sync/status', 'GET'),
    ('/health', 'GET'),
    ('/static/<path:filename>', 'GET')
]


def test_route_table_is_unchanged(backend):
    actual = sorted(
        (rule.rule, ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))))
        for rule in backend.app.url_map.iter_rules()
    )
    expected = sorted(EXPECTED_ROUTES)
    assert [r for r in expected if r not in actual] == [], "routes removed or changed"
    assert [r for r in actual if r not in expected] == [], "new routes: add them to EXPECTED_ROUTES"


def test_health_endpoints(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    assert client.get("/api/health").get_json() == {"status": "ok"}
