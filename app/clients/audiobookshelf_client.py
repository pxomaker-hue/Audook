"""
Audiobookshelf API client for audiobook discovery and streaming
"""

from typing import Optional, List, Dict, Any
import re
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

from app.utils import logger


class AudiobookshelfClient:
    """Client for Audiobookshelf server audiobook operations"""

    def __init__(self, url: str, username: str, password: str):
        """
        Initialize Audiobookshelf client

        Args:
            url: Audiobookshelf server URL (e.g., http://192.168.1.100:80)
            username: Audiobookshelf username
            password: Audiobookshelf password
        """
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.auth_token = None
        self._author_cache: Dict[str, Dict[str, Optional[str]]] = {}
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Audiobookshelf server"""
        try:
            response = self.session.post(
                f"{self.url}/login",
                json={"username": self.username, "password": self.password}
            )
            response.raise_for_status()

            data = response.json()
            self.auth_token = data.get("user", {}).get("token")

            if self.auth_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                logger.info("Authenticated with Audiobookshelf server")
            else:
                logger.error("Failed to get auth token from Audiobookshelf")
                raise Exception("No auth token received")

        except Exception as e:
            logger.error(f"Failed to authenticate with Audiobookshelf: {e}")
            raise

    def get_libraries(self) -> List[Dict[str, Any]]:
        """Get all libraries from server"""
        try:
            response = self.session.get(f"{self.url}/api/libraries")
            response.raise_for_status()

            libraries = []
            for lib in response.json().get("libraries", []):
                libraries.append({
                    "id": lib["id"],
                    "name": lib["name"],
                    "type": "audiobookshelf",
                    "source": "audiobookshelf"
                })

            logger.info(f"Found {len(libraries)} libraries")
            return libraries

        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []

    def get_audiobooks(self, library_id: str) -> List[Dict[str, Any]]:
        """Get audiobooks from a library"""
        try:
            response = self.session.get(
                f"{self.url}/api/libraries/{library_id}/items"
            )
            response.raise_for_status()

            audiobooks = []
            for item in response.json().get("results", []):
                # The list endpoint only returns summary media (no audioFiles/chapters),
                # so fetch the full item to get the actual track list.
                item_id = item.get("id")
                try:
                    detail_response = self.session.get(f"{self.url}/api/items/{item_id}")
                    detail_response.raise_for_status()
                    full_item = detail_response.json()
                except Exception as e:
                    logger.warning(f"Failed to fetch item details for {item_id}: {e}")
                    continue

                audiobook = self._parse_audiobook(full_item, library_id)
                if audiobook:
                    audiobooks.append(audiobook)

            logger.info(f"Found {len(audiobooks)} audiobooks in library {library_id}")
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to get audiobooks: {e}")
            return []

    def get_audiobook_details(self, library_id: str, book_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific audiobook"""
        try:
            response = self.session.get(f"{self.url}/api/items/{book_id}")
            response.raise_for_status()

            return self._parse_audiobook(response.json(), library_id)

        except Exception as e:
            logger.error(f"Failed to get audiobook details: {e}")
            return None

    @staticmethod
    def _join_names(items: List[Any]) -> str:
        """Join an ABS metadata array (authors/narrators/series) into a
        comma-separated string. Items can be plain strings or {id, name, ...}
        dicts depending on the field and how the library was tagged/matched -
        never assume one or the other."""
        if not items:
            return ""
        names = []
        for item in items:
            name = item.get("name") if isinstance(item, dict) else item
            if name:
                names.append(str(name))
        return ", ".join(names)

    def _parse_audiobook(self, book: Dict[str, Any], library_id: str) -> Optional[Dict[str, Any]]:
        """Parse Audiobookshelf book to standard format"""
        try:
            book_id = book.get("id")
            media = book.get("media", {})
            metadata = media.get("metadata", {})

            # Calculate total duration
            total_duration = 0.0
            chapters = []

            # Process audio files
            audio_files = media.get("audioFiles", [])
            for idx, audio_file in enumerate(audio_files):
                duration = audio_file.get("duration", 0.0)
                total_duration += duration

                chapter = {
                    "id": audio_file.get("ino", f"abs_file_{idx}"),
                    "title": audio_file.get("metaTags", {}).get("tagTitle") or f"Chapitre {idx + 1}",
                    "index": idx,
                    "duration": duration,
                    "audio_file": self._get_streaming_url(library_id, book_id, audio_file.get("ino"))
                }
                chapters.append(chapter)

            # Some libraries tag every single track with the same (or a
            # generic "Chapter N") title - ABS itself shows "Chapter 1" for
            # all of them in that case. Prefix the real chapter number so
            # the player can at least tell chapters apart, instead of e.g.
            # 40 identical "Chapitre" entries.
            titles = [c["title"] for c in chapters]
            if len(set(titles)) < len(titles):
                for idx, c in enumerate(chapters):
                    if re.match(r'^chapitre\s*\d+$|^chapter\s*\d+$', c["title"].strip(), re.IGNORECASE):
                        c["title"] = f"Chapitre {idx + 1}"
                    else:
                        c["title"] = f"Chapitre {idx + 1} - {c['title']}"

            # The full item endpoint (/api/items/{id}) returns authors/series as
            # arrays of {id, name} (first-class ABS entities), but narrators has
            # no entity of its own - it's always a plain array of strings. A
            # book whose narrator ABS didn't resolve to an author-like object
            # (seen on some imported libraries) used to crash this whole parse
            # ('str' object has no attribute 'get'), silently dropping the book
            # from every future scan - hence _join_names() below, which accepts
            # either shape for any of the three fields rather than assuming.
            authors = metadata.get("authors") or []
            author = self._join_names(authors) or metadata.get("authorName") or "Unknown Author"

            narrators = metadata.get("narrators") or []
            narrator = self._join_names(narrators) or metadata.get("narratorName") or None

            series = metadata.get("series") or []
            series_names = self._join_names(series) if isinstance(series, list) else series
            # ABS's per-series "sequence" (tome/book number, e.g. "7" or "2.5"
            # for a novella) - only meaningful for the first series entry,
            # same as series_names only really covering the common single-series
            # case. Used to sort a series' books in reading order instead of
            # alphabetically by title.
            series_sequence = None
            if isinstance(series, list) and series and isinstance(series[0], dict):
                series_sequence = series[0].get("sequence")

            first_author = authors[0] if authors and isinstance(authors[0], dict) else None
            author_info = self._get_author_info(first_author["id"]) if first_author and first_author.get("id") else {}

            audiobook = {
                "id": f"abs_{book_id}",
                "title": metadata.get("title", "Unknown"),
                "author": author,
                "narrator": narrator,
                "description": metadata.get("description"),
                "cover_url": self._get_cover_url(library_id, book_id),
                "chapters": chapters,
                "duration": total_duration,
                "extra_metadata": {
                    "genre": metadata.get("genres", []),
                    "language": metadata.get("language"),
                    "publish_year": metadata.get("publishedYear"),
                    "series": series_names,
                    "series_sequence": series_sequence,
                    "author_bio": author_info.get("bio"),
                    "author_photo": author_info.get("photo")
                }
            }

            return audiobook

        except Exception as e:
            logger.error(f"Failed to parse audiobook: {e}")
            return None

    def _get_author_info(self, author_id: str) -> Dict[str, Optional[str]]:
        """Get an author's bio/photo, cached for the lifetime of this client"""
        if author_id in self._author_cache:
            return self._author_cache[author_id]

        info: Dict[str, Optional[str]] = {"bio": None, "photo": None}
        try:
            response = self.session.get(f"{self.url}/api/authors/{author_id}")
            response.raise_for_status()
            data = response.json()
            info["bio"] = data.get("description") or None
            if data.get("imagePath"):
                info["photo"] = f"{self.url}/api/authors/{author_id}/image?token={self.auth_token}"
        except Exception as e:
            logger.warning(f"Failed to get author info for {author_id}: {e}")

        self._author_cache[author_id] = info
        return info

    def _get_streaming_url(self, library_id: str, book_id: str, file_ino: str) -> Optional[str]:
        """Get direct streaming URL for a single audio file"""
        try:
            return f"{self.url}/api/items/{book_id}/file/{file_ino}?token={self.auth_token}"
        except Exception as e:
            logger.error(f"Failed to get streaming URL: {e}")
            return None

    def _get_cover_url(self, library_id: str, book_id: str) -> Optional[str]:
        """Get cover art URL"""
        try:
            return f"{self.url}/api/items/{book_id}/cover?token={self.auth_token}"
        except Exception as e:
            logger.error(f"Failed to get cover URL: {e}")
            return None

    def get_user_progress(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get the current user's progress on a library item.

        Audiobookshelf tracks progress as a single "currentTime" - a position
        within the whole item's continuous timeline, not per audio-file - so
        the caller is responsible for converting that back into a
        chapter_index/position_in_chapter pair."""
        try:
            response = self.session.get(f"{self.url}/api/me")
            response.raise_for_status()
            data = response.json()

            for entry in data.get("mediaProgress", []):
                if entry.get("libraryItemId") == item_id:
                    return {
                        "position_seconds": entry.get("currentTime", 0.0),
                        "duration": entry.get("duration", 0.0),
                        "finished": bool(entry.get("isFinished", False)),
                        "last_update": entry.get("lastUpdate")
                    }
            return None

        except Exception as e:
            logger.error(f"Failed to get user progress: {e}")
            return None

    def set_user_progress(self, item_id: str, position_seconds: float, duration_seconds: float, finished: bool = False):
        """Push the current position (as a whole-item cumulative time) to Audiobookshelf"""
        try:
            progress_fraction = (position_seconds / duration_seconds) if duration_seconds else 0.0
            response = self.session.patch(
                f"{self.url}/api/me/progress/{item_id}",
                json={
                    "currentTime": position_seconds,
                    "duration": duration_seconds,
                    "progress": max(0.0, min(1.0, progress_fraction)),
                    "isFinished": finished
                }
            )
            response.raise_for_status()
            logger.info(f"Pushed progress for item {item_id} to Audiobookshelf")

        except Exception as e:
            logger.warning(f"Failed to push user progress to Audiobookshelf: {e}")

    def test_connection(self) -> bool:
        """Test connection to Audiobookshelf server"""
        try:
            response = self.session.get(f"{self.url}/ping")
            response.raise_for_status()
            logger.info("Audiobookshelf connection test successful")
            return True
        except Exception as e:
            logger.error(f"Audiobookshelf connection test failed: {e}")
            return False
