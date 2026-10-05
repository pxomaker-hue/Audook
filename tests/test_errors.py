"""500 responses must not leak exception text; the detail goes to the log."""
import logging

import pytest

from app.api.context import services

SECRET = r"C:\Users\someone\secret\path.db: OperationalError near 'SELECT'"


class _Boom:
    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise RuntimeError(SECRET)
        return fail


def test_route_errors_do_not_leak_the_exception_text(client, caplog):
    services.library = _Boom()
    with caplog.at_level(logging.ERROR):
        response = client.get("/api/books")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Erreur interne du serveur"}
    assert "secret" not in response.get_data(as_text=True)


def test_the_full_detail_and_traceback_still_reach_the_log(client, caplog):
    services.library = _Boom()
    with caplog.at_level(logging.ERROR):
        client.get("/api/books")
    text = caplog.text
    assert "OperationalError" in text            # the real message is logged...
    assert "Traceback" in text                   # ...with its traceback
    assert "GET /api/books" in text              # ...and which request failed


def test_uncaught_exceptions_get_a_json_500_not_an_html_page(backend, db):
    with backend.app.test_request_context("/api/whatever"):
        try:
            raise RuntimeError(SECRET)
        except RuntimeError as error:
            response = backend.app.handle_user_exception(error)
    assert response.status_code == 500
    assert response.get_json() == {"error": "Erreur interne du serveur"}


def test_http_errors_keep_their_own_status(client, db):
    assert client.get("/api/does-not-exist").status_code == 404
    assert client.put("/api/health").status_code == 405


def test_no_route_returns_raw_exception_text_anymore():
    from pathlib import Path
    offenders = [
        f"{p.name}:{i}"
        for p in Path(__file__).resolve().parent.parent.joinpath("app", "api").glob("*.py")
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if "'error': str(e)" in line
    ]
    assert offenders == []
