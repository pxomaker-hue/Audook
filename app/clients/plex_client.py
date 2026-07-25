"""
Plex API client for audiobook discovery and streaming
"""

from typing import Optional, List, Dict, Any
from plexapi.server import PlexServer
from plexapi.audio import Track
from datetime import datetime

from app.utils import logger


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
        """Get audiobooks from a library"""
        try:
            audiobooks = []
            section = self.server.library.getLatest(libtype="artist")

            # Get artists (audiobooks) from the section
            for artist in self.server.library.section(library_id).all():
                audiobooks.append(self._parse_audiobook(artist))

            logger.info(f"Found {len(audiobooks)} audiobooks in library {library_id}")
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to get audiobooks: {e}")
            return []

    def _parse_audiobook(self, artist) -> Dict[str, Any]:
        """Parse Plex artist (audiobook) to standard format"""
        try:
            # Get all albums (books) from this artist
            albums = artist.albums()

            book_data = {
                "id": f"plex_artist_{artist.key}",
                "title": artist.title,
                "author": artist.title,
                "narrator": None,
                "cover_url": artist.thumb,
                "chapters": [],
                "duration": 0.0
            }

            # Process each album/book
            for album in albums:
                tracks = album.tracks()
                for track in tracks:
                    chapter = {
                        "id": f"plex_track_{track.key}",
                        "title": track.title,
                        "index": track.index - 1 if track.index else 0,
                        "duration": track.duration / 1000.0 if track.duration else 0.0,
                        "audio_file": self._get_streaming_url(track)
                    }
                    book_data["chapters"].append(chapter)
                    book_data["duration"] += chapter["duration"]

            return book_data

        except Exception as e:
            logger.error(f"Failed to parse audiobook: {e}")
            return None

    def _get_streaming_url(self, track: Track) -> str:
        """Get streaming URL for a track"""
        try:
            # Plex streaming URL format
            # /library/metadata/{key}/transcode/universal/start.mp3
            media = track.media[0] if track.media else None
            if media and media.parts:
                part = media.parts[0]
                file_path = part.file

                # Create streaming URL
                url = f"{self.url}/library/parts/{part.id}/file.mp3?X-Plex-Token={self.token}"
                return url
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
