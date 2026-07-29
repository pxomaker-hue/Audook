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

import re
from typing import Optional, Dict, List, Any
from urllib.parse import quote

import requests

from app.utils import logger

REQUEST_TIMEOUT = 5
USER_AGENT = "Audook/1.0 (audiobook library manager)"
UNKNOWN_AUTHOR_NAMES = ("unknown author", "unknown", "")

# Audible's own (unauthenticated, read-only) catalog search API - the same
# endpoint their own web/app clients use, and the one audiobook tools like
# Audiobookshelf and audible-cli already rely on for exactly this purpose.
# Hardcoded to the French store since these are audiobooks and real
# audiobook-specific fields (narrator, series, genre) only exist here -
# Open Library/Google Books are book-catalog databases that rarely carry
# either.
AUDIBLE_HOST = "api.audible.fr"

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


def _search_open_library(title: str, author: Optional[str], limit: int, french_only: bool = False) -> List[Dict[str, Any]]:
    try:
        if french_only:
            # Open Library only honors a language filter when it's part of
            # the combined `q` field query (`title:"..." language:fre`) -
            # passing separate `title=`/`language=` params silently produces
            # an empty query and zero results.
            query = f'title:"{title}" language:fre'
            if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
                query += f' author:"{author}"'
            params = {"q": query, "limit": limit}
        else:
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
                # Only trust the language flag when it came from a query we
                # actually restricted to French - the doc-level `language`
                # field is unreliable (often missing) on unrestricted results,
                # which is how non-French matches used to get mislabeled.
                "is_french": french_only
            })
        return candidates

    except requests.RequestException as e:
        logger.warning(f"Open Library search failed for '{title}': {e}")
        return []


def _search_google_books(title: str, author: Optional[str], limit: int, french_only: bool = False) -> List[Dict[str, Any]]:
    try:
        query = f"intitle:{title}"
        if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
            query += f"+inauthor:{author}"

        params = {"q": query, "maxResults": limit}
        if french_only:
            params["langRestrict"] = "fr"

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
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
                # Same reasoning as Open Library: `langRestrict` is an actual
                # server-side filter, so a hit from that pass is a verified
                # French edition. The unrestricted pass's own `language`
                # field is kept as a secondary (weaker) signal only.
                "is_french": french_only or vi.get("language") == "fr"
            })
        return candidates

    except requests.RequestException as e:
        logger.warning(f"Google Books search failed for '{title}': {e}")
        return []


def _strip_html(value: Optional[str]) -> Optional[str]:
    """Audible's summary fields come as HTML (<p>, <b>, etc) - plain text
    is what every other source in this file already returns, so strip tags
    for a consistent result regardless of which source matched."""
    if not value:
        return value
    text = re.sub(r'<[^>]+>', ' ', value)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _search_audible(title: str, author: Optional[str], limit: int) -> List[Dict[str, Any]]:
    try:
        keywords = title
        if author and author.strip().lower() not in UNKNOWN_AUTHOR_NAMES:
            keywords = f"{title} {author}"

        response = requests.get(
            f"https://{AUDIBLE_HOST}/1.0/catalog/products",
            params={
                "keywords": keywords,
                "num_results": limit,
                "products_sort_by": "Relevance",
                "response_groups": "product_desc,media,contributors,series,category_ladders"
            },
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code != 200:
            return []

        products = response.json().get("products") or []
        candidates = []
        for product in products:
            asin = product.get("asin")
            if not asin or not product.get("title"):
                continue
            authors = ", ".join(a["name"] for a in (product.get("authors") or []) if a.get("name")) or None
            images = product.get("product_images") or {}
            cover_url = images.get("500") or images.get("1024") or images.get("2400")
            candidates.append({
                "work_key": f"audible:{asin}",
                "title": product.get("title"),
                "author": authors,
                "year": (product.get("release_date") or "")[:4] or None,
                "cover_url": cover_url,
                # api.audible.fr is the French store - not a guarantee every
                # result is a French-language edition, but a reasonable
                # default given the store it came from.
                "is_french": True
            })
        return candidates

    except requests.RequestException as e:
        logger.warning(f"Audible search failed for '{title}': {e}")
        return []


def search_book_candidates(title: str, author: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
    """Search Audible, Open Library and Google Books for candidate matches
    for a book, for use in a manual "Associer" (match) picker. Audible
    results are ranked first - since these are audiobooks, an Audible match
    carries real audiobook-specific data (narrator, series, genre) that
    Open Library/Google Books - book-catalog databases - usually lack.
    Each source's failure is non-fatal - results just come from whichever
    source(s) responded.

    Runs a French-restricted pass first for Open Library/Google (using each
    API's actual language filter, not a guessed field) so well-known
    translated books - e.g. Harry Potter - are reliably found in French, and
    so the "is_french" flag on a result is verified rather than a
    best-effort guess."""
    if not title:
        return []

    audible_candidates = _search_audible(title, author, limit)
    fr_ol = _search_open_library(title, author, limit, french_only=True)
    fr_google = _search_google_books(title, author, limit, french_only=True)

    # Only bother with the broader, unrestricted passes if the above didn't
    # already fill the quota.
    remaining = max(0, limit - len(audible_candidates) - len(fr_ol) - len(fr_google))
    ol_candidates = _search_open_library(title, author, limit) if remaining else []
    google_candidates = _search_google_books(title, author, limit) if remaining else []

    seen_keys = set()
    combined = []
    for candidate in audible_candidates + fr_ol + fr_google + ol_candidates + google_candidates:
        key = candidate["work_key"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        combined.append(candidate)

    # A wrong/messy author (common on local-file scans, e.g. a translator
    # credit or a mangled tag) makes every author-filtered query above come
    # back empty even though the title alone would have matched fine - retry
    # title-only before giving up.
    if not combined and author:
        return search_book_candidates(title, author=None, limit=limit)

    combined.sort(key=lambda c: (
        0 if c["work_key"].startswith("audible:") else 1,
        0 if c.get("is_french") else 1
    ))
    return combined[:limit]


def _get_open_library_work_details(work_key: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"description": None, "cover_url": None, "genre": None}
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

            # Open Library has no dedicated "genre" field - its free-text
            # "subjects" list is the closest equivalent, so use the first
            # one as a best-effort genre tag.
            subjects = data.get("subjects") or []
            if subjects:
                result["genre"] = subjects[0]
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Open Library work details for '{work_key}': {e}")

    return result


def _get_google_book_details(item_id: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"description": None, "cover_url": None, "genre": None}
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
            categories = vi.get("categories") or []
            if categories:
                result["genre"] = categories[0]
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Google Books details for '{item_id}': {e}")

    return result


def _get_audible_details(asin: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {
        "description": None, "cover_url": None, "genre": None,
        "narrator": None, "series": None, "series_sequence": None
    }
    try:
        response = requests.get(
            f"https://{AUDIBLE_HOST}/1.0/catalog/products/{asin}",
            # product_extended_attrs is what actually carries publisher_summary
            # (the full back-cover description) - without it, only the short
            # merchandising_summary teaser comes back, cut off mid-sentence.
            params={"response_groups": "product_desc,media,contributors,series,category_ladders,product_extended_attrs"},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code == 200:
            product = response.json().get("product", {})
            # publisher_summary is the full back-cover-style description;
            # merchandising_summary is a short marketing teaser (often a
            # single truncated sentence ending in "...") - prefer the real
            # one, only falling back to the teaser if that's all there is.
            result["description"] = _strip_html(product.get("publisher_summary") or product.get("merchandising_summary"))

            images = product.get("product_images") or {}
            result["cover_url"] = images.get("500") or images.get("1024") or images.get("2400")

            narrators = product.get("narrators") or []
            if narrators:
                result["narrator"] = ", ".join(n["name"] for n in narrators if n.get("name")) or None

            series_list = product.get("series") or []
            if series_list:
                result["series"] = series_list[0].get("title")
                result["series_sequence"] = series_list[0].get("sequence")

            # category_ladders is a list of {"ladder": [{"name": ...}, ...], "root": "Genres"}
            # - the last entry in a ladder is the most specific genre tag.
            for ladder_entry in (product.get("category_ladders") or []):
                items = ladder_entry.get("ladder") or []
                if items:
                    result["genre"] = items[-1].get("name")
                    break
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Audible details for '{asin}': {e}")

    return result


def get_audible_chapters(asin: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch Audible's own chapter list (real titles, in the book's actual
    language) for an ASIN - used to replace generic/duplicate per-file
    chapter titles (e.g. every file just says "Chapter 1" because the
    source files/server had no real per-chapter tag data). Returns None on
    any failure so callers can skip cleanly."""
    try:
        response = requests.get(
            f"https://{AUDIBLE_HOST}/1.0/content/{asin}/metadata",
            params={"response_groups": "chapter_info"},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code != 200:
            return None

        raw_chapters = (
            response.json().get("content_metadata", {})
            .get("chapter_info", {})
            .get("chapters") or []
        )
        if not raw_chapters:
            return None

        return [
            {"title": c.get("title"), "duration": (c.get("length_ms") or 0) / 1000.0}
            for c in raw_chapters
        ]
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Audible chapters for '{asin}': {e}")
        return None


def get_book_work_details(work_key: str) -> Dict[str, Optional[str]]:
    """Fetch full description/cover (and, for Audible, narrator/series/genre
    too) for a candidate returned by search_book_candidates (used once the
    user picks one)."""
    if work_key.startswith("google:"):
        return _get_google_book_details(work_key[len("google:"):])
    if work_key.startswith("audible:"):
        return _get_audible_details(work_key[len("audible:"):])
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
