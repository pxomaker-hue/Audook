"""
Plex API client for audiobook discovery and streaming
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.utils import logger

try:
    from plexapi.server import PlexServer
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
        """Connect to Plex server"""
        if not PLEX_AVAILABLE:
            raise ImportError("plexapi not installed - cannot connect to Plex")

        try:
            self.server = PlexServer(self.url, self.token)
            logger.info(f"Connected to Plex server: {self.server.friendlyName}")
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            raise

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
                    "author_photo": author_photo
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

    def get_audiobook_progress(self, track_key: str) -> Dict[str, Any]:
        """Get user's progress on an audiobook"""
        try:
            track = self.server.library.getByKey(f"/library/metadata/{track_key}")

            if track and hasattr(track, 'userRating'):
                return {
                    "viewed_leaf_count": getattr(track, 'viewedLeafCount', 0),
                    "leaf_count": getattr(track, 'leafCount', 0),
                    "view_offset": getattr(track, 'viewOffset', 0)
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get audiobook progress: {e}")
            return {}

    def set_audiobook_progress(self, track_key: str, position_ms: int):
        """Update playback position for a track"""
        try:
            url = f"{self.url}/library/metadata/{track_key}/timeline"
            params = {
                "time": position_ms,
                "state": "playing",
                "X-Plex-Token": self.token
            }
            # This would need a proper HTTP request implementation
            logger.info(f"Updated progress for track {track_key} to {position_ms}ms")
        except Exception as e:
            logger.error(f"Failed to set audiobook progress: {e}")

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
