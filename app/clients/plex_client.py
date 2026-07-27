"""
Plex API client for audiobook discovery and streaming
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.utils import logger

try:
    from plexapi.server import PlexServer
    from plexapi.myplex import MyPlexAccount
    from plexapi.audio import Track
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False
    logger.warning("plexapi not installed - Plex support disabled")


class PlexClient:
    """Client for Plex server audiobook operations"""

    def __init__(self, url: str, token: str):
        """
        Initialize Plex client

        Args:
            url: Plex server URL (e.g., http://192.168.1.100:32400)
            token: Plex API token
        """
        self.url = url
        self.token = token
        self.server: Optional[PlexServer] = None
        self._connect()

    def _connect(self):
        """Connect to Plex server.

        Tries the account-based connection first: authenticating via the
        account token and asking plex.tv for this server's resource lets
        plexapi test every known connection (local network AND the
        plex.tv remote-access relay) and automatically pick whichever one
        is actually reachable right now - the same thing the official Plex
        apps do, and exactly what makes Plex usable outside the home
        network without any VPN/manual URL juggling.

        Falls back to a direct connection using the stored `url` (the old
        behavior) if the account lookup fails for any reason - invalid/
        server-only token, no network path to plex.tv, account has no
        matching server resource, etc. This keeps local-only setups working
        exactly as before.
        """
        if not PLEX_AVAILABLE:
            raise ImportError("plexapi not installed - cannot connect to Plex")

        try:
            self.server = self._connect_via_account()
            if self.server:
                logger.info(f"Connected to Plex server via account: {self.server.friendlyName}")
                return
        except Exception as e:
            logger.warning(f"Account-based Plex connection failed, falling back to direct URL: {e}")

        try:
            self.server = PlexServer(self.url, self.token)
            logger.info(f"Connected to Plex server: {self.server.friendlyName}")
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            raise

    def _connect_via_account(self) -> Optional["PlexServer"]:
        """Resolve this server via the plex.tv account and let plexapi pick
        the best reachable connection. Returns None (not an exception) if the
        account has no server resource to match, so the caller falls back to
        the direct URL cleanly."""
        account = MyPlexAccount(token=self.token)
        resources = [r for r in account.resources() if "server" in (r.provides or "")]
        if not resources:
            return None

        # Prefer a resource whose known connections include the host we
        # have on file (disambiguates when the account has several Plex
        # servers) - otherwise just take the first server resource.
        from urllib.parse import urlparse
        target_host = urlparse(self.url).hostname
        resource = next(
            (r for r in resources if any(target_host and target_host in (c.address or "") for c in r.connections)),
            resources[0]
        )
        return resource.connect()

    def get_audiobook_libraries(self) -> List[Dict[str, Any]]:
        """Get all audiobook libraries from server"""
        try:
            libraries = []
            for section in self.server.library.sections():
                if section.type == "artist":  # Audiobooks are in music type on Plex
                    libraries.append({
                        "id": section.key,
                        "name": section.title,
                        "type": "plex",
                        "source": "plex"
                    })
            logger.info(f"Found {len(libraries)} audiobook libraries")
            return libraries
        except Exception as e:
            logger.error(f"Failed to get audiobook libraries: {e}")
            return []

    def get_audiobooks(self, library_id: str) -> List[Dict[str, Any]]:
        """Get audiobooks from a library.

        Plex organizes audiobooks as Artist=Author / Album=Book / Track=Chapter.
        Each album is returned as one audiobook (not the whole artist, which
        would otherwise flatten every book by that author into a single item).
        """
        try:
            audiobooks = []

            for artist in self.server.library.sectionByID(int(library_id)).all():
                author_bio = artist.summary or None
                author_photo = self._get_image_url(artist.thumb)
                for album in artist.albums():
                    audiobook = self._parse_audiobook(album, artist.title, author_bio, author_photo)
                    if audiobook:
                        audiobooks.append(audiobook)

            logger.info(f"Found {len(audiobooks)} audiobooks in library {library_id}")
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to get audiobooks: {e}")
            return []

    def _parse_audiobook(
        self, album, author_name: str, author_bio: Optional[str] = None, author_photo: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse a Plex album (audiobook) to standard format"""
        try:
            tracks = sorted(album.tracks(), key=lambda t: t.index or 0)

            chapters = []
            total_duration = 0.0
            for idx, track in enumerate(tracks):
                duration = (track.duration or 0) / 1000.0
                total_duration += duration

                chapters.append({
                    "id": f"plex_track_{track.ratingKey}",
                    "title": track.title or f"Chapter {idx + 1}",
                    "index": idx,
                    "duration": duration,
                    "audio_file": self._get_streaming_url(track)
                })

            # Plex has no native "book series" field for music-organized audiobooks,
            # but collections are commonly used for that purpose - best-effort.
            series = None
            collections = getattr(album, "collections", None) or []
            collection_names = [c.tag for c in collections if getattr(c, "tag", None)]
            if collection_names:
                series = ", ".join(collection_names)

            return {
                "id": f"plex_album_{album.ratingKey}",
                "title": album.title,
                "author": author_name,
                "narrator": None,
                "description": album.summary or None,
                "cover_url": self._get_image_url(album.thumb),
                "chapters": chapters,
                "duration": total_duration,
                "extra_metadata": {
                    "author_bio": author_bio,
                    "author_photo": author_photo,
                    "series": series
                }
            }

        except Exception as e:
            logger.error(f"Failed to parse audiobook: {e}")
            return None

    def _get_image_url(self, thumb_path: Optional[str]) -> Optional[str]:
        """Build an absolute, authenticated URL for a Plex-relative image path"""
        if not thumb_path:
            return None
        return f"{self.url}{thumb_path}?X-Plex-Token={self.token}"

    def _get_streaming_url(self, track) -> Optional[str]:
        """Get streaming URL for a track"""
        try:
            media = track.media[0] if track.media else None
            if media and media.parts:
                part = media.parts[0]
                # part.key is already the correct, fully-formed download path
                # (e.g. /library/parts/8341/1784986739/file.mp3) - do not
                # reconstruct it manually, it has more segments than just the id.
                return f"{self.url}{part.key}?X-Plex-Token={self.token}"
        except Exception as e:
            logger.error(f"Failed to get streaming URL: {e}")

        return None

    def _album_for_book(self, book_id: str):
        """Resolve a book id (e.g. 'plex_album_1234') back to its Plex album"""
        rating_key = book_id.replace("plex_album_", "", 1)
        return self.server.fetchItem(int(rating_key))

    def pull_progress(self, book_id: str, chapters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Read progress from Plex. Each chapter is a separate Plex track, so
        this walks the tracks in order and reports the first one that isn't
        fully watched as the current chapter/position."""
        try:
            album = self._album_for_book(book_id)
            tracks = sorted(album.tracks(), key=lambda t: t.index or 0)
            if not tracks:
                return None

            for idx, track in enumerate(tracks):
                view_offset_ms = getattr(track, 'viewOffset', 0) or 0
                view_count = getattr(track, 'viewCount', 0) or 0
                if view_count > 0 and view_offset_ms == 0:
                    # Fully watched, no partial offset left over - move on
                    continue
                return {
                    "chapter_index": idx,
                    "position_seconds": view_offset_ms / 1000.0,
                    "finished": False
                }

            # Every track has been watched
            return {"chapter_index": len(tracks) - 1, "position_seconds": 0.0, "finished": True}

        except Exception as e:
            logger.warning(f"Failed to pull progress from Plex: {e}")
            return None

    def push_progress(self, book_id: str, chapters: List[Dict[str, Any]], chapter_index: int,
                       position_seconds: float, finished: bool = False) -> bool:
        """Push progress to Plex: mark chapters before the current one as
        watched, and report the live position on the current one."""
        try:
            album = self._album_for_book(book_id)
            tracks = sorted(album.tracks(), key=lambda t: t.index or 0)

            for idx, track in enumerate(tracks):
                try:
                    if finished or idx < chapter_index:
                        track.markWatched()
                    elif idx == chapter_index:
                        duration_ms = int(track.duration or 0)
                        track.updateTimeline(int(position_seconds * 1000), state='paused', duration=duration_ms)
                except Exception as e:
                    logger.warning(f"Failed to push progress for track {idx} of {book_id}: {e}")

            return True

        except Exception as e:
            logger.warning(f"Failed to push progress to Plex: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to Plex server"""
        try:
            if self.server:
                _ = self.server.library.sections()
                logger.info("Plex connection test successful")
                return True
        except Exception as e:
            logger.error(f"Plex connection test failed: {e}")

        return False
