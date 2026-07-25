"""
API clients for streaming services
Supports Plex and Audiobookshelf
"""

from app.clients.plex_client import PlexClient
from app.clients.audiobookshelf_client import AudiobookshelfClient

__all__ = [
    "PlexClient",
    "AudiobookshelfClient",
]
