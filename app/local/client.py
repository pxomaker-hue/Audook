"""
Local client - abstracts local folders as if they were a server
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

from app.models import Audiobook, Library
from app.utils import logger
from .scanner import LocalAudiobookScanner, get_local_library


class LocalClient:
    """Client for accessing local audiobook folders"""

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        self.base_url = str(self.folder_path)
        self.scanner = LocalAudiobookScanner()
        self._audiobooks_cache: Dict[str, List[Audiobook]] = {}

    async def ping(self) -> bool:
        """Check if folder is accessible"""
        return self.folder_path.exists() and self.folder_path.is_dir()

    async def get_libraries(self) -> List[Library]:
        """Get libraries (just return the main folder as one library)"""
        if await self.ping():
            return [get_local_library(self.folder_path)]
        return []

    async def get_audiobooks(
        self,
        library_id: str,
        limit: int = 100,
        offset: int = 0,
        filter_by: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Audiobook]:
        """Get audiobooks from local folder"""
        if library_id not in self._audiobooks_cache:
            self._audiobooks_cache[library_id] = await self.scanner.scan_folder(self.folder_path)

        audiobooks = self._audiobooks_cache[library_id]

        # Filter if requested
        if filter_by:
            audiobooks = [
                ab for ab in audiobooks
                if filter_by.lower() in ab.title.lower()
                or filter_by.lower() in ab.author.lower()
            ]

        # Sort
        if sort_by == "title":
            audiobooks.sort(key=lambda x: x.title)
        elif sort_by == "author":
            audiobooks.sort(key=lambda x: x.author)

        # Paginate
        return audiobooks[offset : offset + limit]

    async def get_audiobook(self, library_id: str, audiobook_id: str) -> Optional[Audiobook]:
        """Get a specific audiobook"""
        if library_id not in self._audiobooks_cache:
            self._audiobooks_cache[library_id] = await self.scanner.scan_folder(self.folder_path)

        for ab in self._audiobooks_cache[library_id]:
            if ab.id == audiobook_id:
                return ab
        return None

    def close(self):
        """Close the client (no-op for local client)"""
        pass
