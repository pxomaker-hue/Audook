"""
Online metadata enrichment - best-effort lookups used to fill gaps when a
Plex/Audiobookshelf/local source doesn't provide an author bio/photo or a
book description/cover. Every call is non-fatal: network failures just leave
the field empty, they never interrupt a scan.
"""

from typing import Optional, Dict
from urllib.parse import quote

import requests

from app.utils import logger

REQUEST_TIMEOUT = 5
USER_AGENT = "Audook/1.0 (audiobook library manager)"
UNKNOWN_AUTHOR_NAMES = ("unknown author", "unknown", "")

# In-memory caches for the lifetime of the process - author/book metadata
# doesn't change often enough to justify repeating a network call for the
# same name/title within (or across) scans.
_author_cache: Dict[str, Dict[str, Optional[str]]] = {}
_book_cache: Dict[str, Dict[str, Optional[str]]] = {}


def fetch_author_info_online(name: str) -> Dict[str, Optional[str]]:
    """Look up an author's bio/photo on Wikipedia."""
    empty = {"bio": None, "photo": None}
    if not name or name.strip().lower() in UNKNOWN_AUTHOR_NAMES:
        return empty

    cache_key = name.strip().lower()
    if cache_key in _author_cache:
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


def fetch_book_info_online(title: str, author: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Look up a book's description/cover on Open Library."""
    empty = {"description": None, "cover_url": None}
    if not title:
        return empty

    cache_key = f"{title.strip().lower()}::{(author or '').strip().lower()}"
    if cache_key in _book_cache:
        return _book_cache[cache_key]

    result = dict(empty)
    try:
        params = {"title": title, "limit": 1}
        if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
            params["author"] = author

        response = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code == 200:
            docs = response.json().get("docs") or []
            if docs:
                doc = docs[0]

                cover_id = doc.get("cover_i")
                if cover_id:
                    result["cover_url"] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

                work_key = doc.get("key")
                if work_key:
                    work_response = requests.get(
                        f"https://openlibrary.org{work_key}.json",
                        timeout=REQUEST_TIMEOUT,
                        headers={"User-Agent": USER_AGENT}
                    )
                    if work_response.status_code == 200:
                        description = work_response.json().get("description")
                        if isinstance(description, dict):
                            description = description.get("value")
                        result["description"] = description or None

    except requests.RequestException as e:
        logger.warning(f"Online book lookup failed for '{title}': {e}")

    _book_cache[cache_key] = result
    return result
