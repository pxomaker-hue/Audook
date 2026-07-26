"""
Online metadata enrichment - best-effort lookups used to fill gaps when a
Plex/Audiobookshelf/local source doesn't provide an author bio/photo or a
book description/cover, and to power the "Associer" (match) feature that lets
a user manually pick the right online match for a book. Every call is
non-fatal: network failures just leave the field empty, they never interrupt
a scan.

French results are preferred throughout (Wikipedia is queried fr.wikipedia.org
first; Open Library candidates with a French-language edition are ranked
first) per user preference.
"""

from typing import Optional, Dict, List, Any
from urllib.parse import quote

import requests

from app.utils import logger

REQUEST_TIMEOUT = 5
USER_AGENT = "Audook/1.0 (audiobook library manager)"
UNKNOWN_AUTHOR_NAMES = ("unknown author", "unknown", "")

# In-memory caches for the lifetime of the process - author/book metadata
# doesn't change often enough to justify repeating a network call for the
# same name/title within (or across) scans. Bypassed by force=True.
_author_cache: Dict[str, Dict[str, Optional[str]]] = {}
_book_cache: Dict[str, Dict[str, Optional[str]]] = {}


def fetch_author_info_online(name: str, force: bool = False) -> Dict[str, Optional[str]]:
    """Look up an author's bio/photo on Wikipedia (French first, then English)."""
    empty = {"bio": None, "photo": None}
    if not name or name.strip().lower() in UNKNOWN_AUTHOR_NAMES:
        return empty

    cache_key = name.strip().lower()
    if not force and cache_key in _author_cache:
        return _author_cache[cache_key]

    result = dict(empty)
    for lang in ("fr", "en"):
        try:
            response = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(name)}",
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("type") == "disambiguation":
                    continue
                result["bio"] = data.get("extract") or None
                result["photo"] = (data.get("thumbnail") or {}).get("source")
                if result["bio"] or result["photo"]:
                    break
        except requests.RequestException as e:
            logger.warning(f"Online author lookup failed for '{name}' ({lang}): {e}")

    _author_cache[cache_key] = result
    return result


def _search_open_library(title: str, author: Optional[str], limit: int) -> List[Dict[str, Any]]:
    try:
        params = {"title": title, "limit": limit}
        if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
            params["author"] = author

        response = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code != 200:
            return []

        docs = response.json().get("docs") or []
        candidates = []
        for doc in docs:
            work_key = doc.get("key")
            if not work_key:
                continue
            cover_id = doc.get("cover_i")
            candidates.append({
                "work_key": f"ol:{work_key}",
                "title": doc.get("title"),
                "author": ", ".join(doc.get("author_name") or []) or None,
                "year": doc.get("first_publish_year"),
                "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
                "is_french": "fre" in (doc.get("language") or [])
            })
        return candidates

    except requests.RequestException as e:
        logger.warning(f"Open Library search failed for '{title}': {e}")
        return []


def _search_google_books(title: str, author: Optional[str], limit: int) -> List[Dict[str, Any]]:
    try:
        query = f"intitle:{title}"
        if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
            query += f"+inauthor:{author}"

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": query, "maxResults": limit},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code != 200:
            return []

        items = response.json().get("items") or []
        candidates = []
        for item in items:
            item_id = item.get("id")
            vi = item.get("volumeInfo", {})
            if not item_id or not vi.get("title"):
                continue
            thumbnail = (vi.get("imageLinks") or {}).get("thumbnail")
            candidates.append({
                "work_key": f"google:{item_id}",
                "title": vi.get("title"),
                "author": ", ".join(vi.get("authors") or []) or None,
                "year": (vi.get("publishedDate") or "")[:4] or None,
                "cover_url": thumbnail.replace("http://", "https://") if thumbnail else None,
                "is_french": vi.get("language") == "fr"
            })
        return candidates

    except requests.RequestException as e:
        logger.warning(f"Google Books search failed for '{title}': {e}")
        return []


def search_book_candidates(title: str, author: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
    """Search Open Library and Google Books for candidate matches for a book,
    French editions ranked first, for use in a manual "Associer" (match)
    picker. Each source's failure (including Google's anonymous rate limit)
    is non-fatal - results just come from whichever source responded."""
    if not title:
        return []

    ol_candidates = _search_open_library(title, author, limit)
    google_candidates = _search_google_books(title, author, limit)

    # Interleave so one source's ranking doesn't drown out the other, then
    # put French results first overall.
    combined = []
    for a, b in zip(ol_candidates, google_candidates):
        combined.extend([a, b])
    combined.extend(ol_candidates[len(google_candidates):])
    combined.extend(google_candidates[len(ol_candidates):])

    combined.sort(key=lambda c: 0 if c.get("is_french") else 1)
    return combined[:limit]


def _get_open_library_work_details(work_key: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"description": None, "cover_url": None}
    try:
        response = requests.get(
            f"https://openlibrary.org{work_key}.json",
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code == 200:
            data = response.json()
            description = data.get("description")
            if isinstance(description, dict):
                description = description.get("value")
            result["description"] = description or None

            covers = data.get("covers") or []
            if covers:
                result["cover_url"] = f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Open Library work details for '{work_key}': {e}")

    return result


def _get_google_book_details(item_id: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"description": None, "cover_url": None}
    try:
        response = requests.get(
            f"https://www.googleapis.com/books/v1/volumes/{item_id}",
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code == 200:
            vi = response.json().get("volumeInfo", {})
            result["description"] = vi.get("description") or None
            images = vi.get("imageLinks") or {}
            cover = images.get("large") or images.get("medium") or images.get("thumbnail")
            if cover:
                result["cover_url"] = cover.replace("http://", "https://")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Google Books details for '{item_id}': {e}")

    return result


def get_book_work_details(work_key: str) -> Dict[str, Optional[str]]:
    """Fetch full description/cover for a candidate returned by
    search_book_candidates (used once the user picks one)."""
    if work_key.startswith("google:"):
        return _get_google_book_details(work_key[len("google:"):])
    if work_key.startswith("ol:"):
        return _get_open_library_work_details(work_key[len("ol:"):])
    # Backward compatibility with older raw Open Library keys (e.g. cached values)
    return _get_open_library_work_details(work_key)


def fetch_book_info_online(title: str, author: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Look up a book's description/cover on Open Library, preferring a
    French-language edition when one is available. Used for automatic
    enrichment during a scan."""
    empty = {"description": None, "cover_url": None}
    if not title:
        return empty

    cache_key = f"{title.strip().lower()}::{(author or '').strip().lower()}"
    if cache_key in _book_cache:
        return _book_cache[cache_key]

    result = dict(empty)
    candidates = search_book_candidates(title, author, limit=1)
    if candidates:
        best = candidates[0]
        details = get_book_work_details(best["work_key"])
        result["description"] = details.get("description")
        result["cover_url"] = details.get("cover_url") or best.get("cover_url")

    _book_cache[cache_key] = result
    return result
