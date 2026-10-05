"""CORS: the Capacitor app (origin https://localhost) and Electron call the
backend cross-origin, including with an Authorization header, so the preflight
must succeed and answer with the right Access-Control-* headers."""

ORIGIN = "https://localhost"


def preflight(client, path="/api/books", headers="authorization"):
    return client.options(path, headers={
        "Origin": ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": headers,
    })


def test_preflight_allows_the_app_origin_and_authorization_header(client, db):
    response = preflight(client)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] in ("*", ORIGIN)
    assert "authorization" in response.headers["Access-Control-Allow-Headers"].lower()


def test_preflight_passes_even_when_the_api_is_token_protected(client, monkeypatch):
    monkeypatch.setenv("AUDOOK_API_TOKEN", "s3cret")
    assert preflight(client).status_code == 200


def test_actual_responses_carry_the_cors_header(client, db):
    response = client.get("/api/books", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] in ("*", ORIGIN)


def test_rejected_requests_still_carry_the_cors_header(client, monkeypatch):
    # otherwise the browser hides the 401 and the app can't tell "bad token" from "offline"
    monkeypatch.setenv("AUDOOK_API_TOKEN", "s3cret")
    response = client.get("/api/books", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.headers["Access-Control-Allow-Origin"] in ("*", ORIGIN)


def test_custom_token_header_is_allowed_in_preflight(client, db):
    response = preflight(client, headers="x-audook-token")
    assert response.status_code == 200
    assert "x-audook-token" in response.headers["Access-Control-Allow-Headers"].lower()
