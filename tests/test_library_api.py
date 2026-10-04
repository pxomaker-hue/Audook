"""Books, bookmarks, history, collections, equalizer presets and servers
through the real Flask routes against a throwaway SQLite database."""


# ---------- books ----------

def test_books_list_is_empty_on_a_fresh_database(client):
    assert client.get("/api/books").get_json() == []


def test_books_list_and_details(client, seed_book):
    book_id = seed_book()
    books = client.get("/api/books").get_json()
    assert [b["id"] for b in books] == [book_id]
    assert books[0]["title"] == "Test Book"
    assert books[0]["progress_percent"] == 0
    assert books[0]["is_finished"] is False

    details = client.get(f"/api/books/{book_id}").get_json()
    assert details["id"] == book_id
    assert len(details["chapters"]) == 3


def test_unknown_book_details_is_404(client, db):
    assert client.get("/api/books/nope").status_code == 404


def test_mark_finished_and_unfinished(client, seed_book):
    book_id = seed_book()
    client.post(f"/api/books/{book_id}/finished", json={"finished": True})
    assert client.get("/api/books").get_json()[0]["is_finished"] is True
    client.post(f"/api/books/{book_id}/finished", json={"finished": False})
    assert client.get("/api/books").get_json()[0]["is_finished"] is False


def test_in_progress_book_exposes_percent_and_numbered_chapter_title(client, seed_book, monkeypatch):
    monkeypatch.setattr("app.api.progress.progress_sync.push_progress", lambda *a, **k: None)
    book_id = seed_book(durations=(100.0, 100.0))
    client.post(f"/api/books/{book_id}/progress", json={"chapter_index": 1, "position_seconds": 50})
    book = client.get("/api/books").get_json()[0]
    assert book["progress_percent"] == 75.0
    assert book["current_chapter_title"] == "2. Chapter 2"


def test_search_matches_title_and_author(client, seed_book):
    seed_book()
    assert len(client.get("/api/books/search", query_string={"q": "Test"}).get_json()) == 1
    assert len(client.get("/api/books/search", query_string={"q": "Author"}).get_json()) == 1
    assert client.get("/api/books/search", query_string={"q": "zzz"}).get_json() == []


def test_patch_book_updates_fields_and_locks_them(client, seed_book):
    book_id = seed_book()
    client.patch(f"/api/books/{book_id}", json={"title": "Renamed"})
    assert client.get(f"/api/books/{book_id}").get_json()["title"] == "Renamed"


# ---------- bookmarks ----------

def test_bookmark_create_and_delete(client, seed_book):
    book_id = seed_book()
    created = client.post(f"/api/books/{book_id}/bookmarks",
                          json={"chapter_index": 1, "position": 42.0, "title": "Mark"})
    assert created.status_code == 201
    bookmark_id = created.get_json()["id"]
    assert client.get(f"/api/books/{book_id}").get_json()["bookmarks"][0]["id"] == bookmark_id
    assert client.delete(f"/api/bookmarks/{bookmark_id}").status_code == 200
    assert client.get(f"/api/books/{book_id}").get_json()["bookmarks"] == []


def test_bookmark_on_unknown_book_is_404(client, db):
    assert client.post("/api/books/nope/bookmarks", json={"chapter_index": 0, "position": 1}).status_code == 404


# ---------- history ----------

def test_history_starts_empty_and_clear_works(client, db):
    assert client.get("/api/history").get_json() == []
    assert client.delete("/api/history").get_json()["status"] == "cleared"


# ---------- collections ----------

def test_collection_lifecycle(client, seed_book):
    book_id = seed_book()
    created = client.post("/api/collections", json={"name": "  Favoris "}).get_json()
    cid = created["id"]
    assert created["name"] == "Favoris"

    assert client.patch(f"/api/collections/{cid}", json={"name": "Top"}).status_code == 200
    assert client.post(f"/api/collections/{cid}/books", json={"book_id": book_id}).status_code == 200
    listed = client.get("/api/collections").get_json()
    assert listed == [{"id": cid, "name": "Top", "book_ids": [book_id]}]

    assert client.delete(f"/api/collections/{cid}/books/{book_id}").status_code == 200
    assert client.get("/api/collections").get_json()[0]["book_ids"] == []
    assert client.delete(f"/api/collections/{cid}").status_code == 200
    assert client.get("/api/collections").get_json() == []


def test_collection_requires_a_name(client, db):
    assert client.post("/api/collections", json={"name": "   "}).status_code == 400
    assert client.post("/api/collections", json={}).status_code == 400


# ---------- servers ----------

def test_servers_list_hide_and_delete(client, seed_book):
    seed_book()
    servers = client.get("/api/servers").get_json()
    assert [s["id"] for s in servers] == ["srv1"]
    assert servers[0]["hidden"] is False

    client.post("/api/servers/srv1/hidden", json={"hidden": True})
    assert client.get("/api/servers").get_json()[0]["hidden"] is True
    assert client.get("/api/books").get_json() == []  # hidden server's books are filtered out

    assert client.delete("/api/servers/srv1").status_code == 200
    assert client.get("/api/servers").get_json() == []


def test_add_server_rejects_unknown_type(client, db):
    response = client.post("/api/servers", json={"type": "bogus", "name": "x", "url": "http://x"})
    assert response.status_code == 400
