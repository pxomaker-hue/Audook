"""
Audiobookshelf API client
Handles communication with Audiobookshelf server
"""

import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from app.models import Audiobook, Chapter, Library
from app.utils import logger


class AudiobookshelfClient:
    """Client for Audiobookshelf API"""
    
    API_VERSION = "v1"
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/{self.API_VERSION}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Audook/1.0"
            },
            timeout=30.0
        )
    
    async def __aenter__(self):
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    def close(self):
        """Close the client"""
        self._client.close()
    
    async def ping(self) -> bool:
        """Check if server is reachable"""
        try:
            response = await self._client.get("/ping")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def get_libraries(self) -> List[Library]:
        """Get all libraries"""
        try:
            response = await self._client.get("/libraries")
            response.raise_for_status()
            data = response.json()
            
            libraries = []
            for lib_data in data.get("libraries", []):
                libraries.append(Library(
                    id=lib_data.get("id", ""),
                    name=lib_data.get("name", "Unknown"),
                    source="audiobookshelf",
                    server_url=self.base_url,
                    server_name=lib_data.get("serverName", "")
                ))
            return libraries
        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []
    
    async def get_audiobooks(
        self, 
        library_id: str, 
        limit: int = 100, 
        offset: int = 0,
        filter_by: Optional[str] = None,
        sort_by: Optional[str] = None
    ) -> List[Audiobook]:
        """Get audiobooks from a library"""
        try:
            params = {
                "libraryId": library_id,
                "limit": limit,
                "offset": offset
            }
            
            if filter_by:
                params["filter"] = filter_by
            if sort_by:
                params["sort"] = sort_by
            
            response = await self._client.get("/libraries/{library_id}/audiobooks", params=params)
            response.raise_for_status()
            data = response.json()
            
            audiobooks = []
            for book_data in data.get("audiobooks", []):
                audiobook = Audiobook(
                    id=book_data.get("id", ""),
                    library_id=library_id,
                    title=book_data.get("title", "Unknown"),
                    author=book_data.get("author", "Unknown"),
                    narrator=book_data.get("narrator"),
                    description=book_data.get("description"),
                    cover=self._get_cover_url(book_data.get("cover")),
                    duration=book_data.get("duration", 0),
                    metadata=book_data.get("metadata", {}),
                    source="audiobookshelf"
                )
                
                # Get chapters
                chapters_data = book_data.get("chapters", [])
                audiobook.chapters = []
                for chap_data in chapters_data:
                    audiobook.chapters.append({
                        "id": chap_data.get("id", ""),
                        "title": chap_data.get("title", "Chapter"),
                        "index": chap_data.get("index", 0),
                        "duration": chap_data.get("duration", 0),
                        "start": chap_data.get("start", 0),
                        "audio_file": chap_data.get("audioFile", "")
                    })
                
                audiobooks.append(audiobook)
            
            return audiobooks
        except Exception as e:
            logger.error(f"Failed to get audiobooks: {e}")
            return []
    
    async def get_audiobook(self, library_id: str, book_id: str) -> Optional[Audiobook]:
        """Get a single audiobook by ID"""
        try:
            response = await self._client.get(f"/libraries/{library_id}/audiobooks/{book_id}")
            response.raise_for_status()
            book_data = response.json()
            
            audiobook = Audiobook(
                id=book_data.get("id", ""),
                library_id=library_id,
                title=book_data.get("title", "Unknown"),
                author=book_data.get("author", "Unknown"),
                narrator=book_data.get("narrator"),
                description=book_data.get("description"),
                cover=self._get_cover_url(book_data.get("cover")),
                duration=book_data.get("duration", 0),
                metadata=book_data.get("metadata", {}),
                source="audiobookshelf"
            )
            
            # Get chapters
            chapters_data = book_data.get("chapters", [])
            audiobook.chapters = []
            for chap_data in chapters_data:
                audiobook.chapters.append({
                    "id": chap_data.get("id", ""),
                    "title": chap_data.get("title", "Chapter"),
                    "index": chap_data.get("index", 0),
                    "duration": chap_data.get("duration", 0),
                    "start": chap_data.get("start", 0),
                    "audio_file": chap_data.get("audioFile", "")
                })
            
            return audiobook
        except Exception as e:
            logger.error(f"Failed to get audiobook: {e}")
            return None
    
    async def get_chapter_audio_url(
        self, 
        library_id: str, 
        book_id: str, 
        chapter_id: str
    ) -> Optional[str]:
        """Get the audio URL for a chapter"""
        try:
            # Audiobookshelf serves audio files directly
            # The audio file path is in the chapter data
            audiobook = await self.get_audiobook(library_id, book_id)
            if not audiobook:
                return None
            
            for chapter in audiobook.chapters:
                if chapter.get("id") == chapter_id:
                    audio_file = chapter.get("audioFile", "")
                    if audio_file:
                        # Construct the full URL
                        return f"{self.base_url}/api/items/{audio_file}/stream"
            
            return None
        except Exception as e:
            logger.error(f"Failed to get chapter audio URL: {e}")
            return None
    
    async def get_book_cover_url(self, library_id: str, book_id: str) -> Optional[str]:
        """Get the cover URL for a book"""
        try:
            audiobook = await self.get_audiobook(library_id, book_id)
            if audiobook and audiobook.cover:
                return audiobook.cover
            return None
        except Exception as e:
            logger.error(f"Failed to get book cover URL: {e}")
            return None
    
    async def search(
        self, 
        library_id: str, 
        query: str, 
        limit: int = 20
    ) -> List[Audiobook]:
        """Search for audiobooks"""
        try:
            params = {
                "libraryId": library_id,
                "query": query,
                "limit": limit
            }
            
            response = await self._client.get("/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            audiobooks = []
            for book_data in data.get("results", []):
                if book_data.get("type") == "audiobook":
                    audiobook = Audiobook(
                        id=book_data.get("id", ""),
                        library_id=library_id,
                        title=book_data.get("title", "Unknown"),
                        author=book_data.get("author", "Unknown"),
                        narrator=book_data.get("narrator"),
                        cover=self._get_cover_url(book_data.get("cover")),
                        duration=book_data.get("duration", 0),
                        source="audiobookshelf"
                    )
                    audiobooks.append(audiobook)
            
            return audiobooks
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_user_progress(
        self, 
        library_id: str, 
        book_id: str
    ) -> Dict[str, Any]:
        """Get user progress for a book"""
        try:
            response = await self._client.get(f"/libraries/{library_id}/audiobooks/{book_id}/progress")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user progress: {e}")
            return {}
    
    async def update_user_progress(
        self, 
        library_id: str, 
        book_id: str, 
        chapter_id: str,
        position: float,
        duration: float
    ) -> bool:
        """Update user progress for a book"""
        try:
            data = {
                "chapterId": chapter_id,
                "position": position,
                "duration": duration
            }
            response = await self._client.post(
                f"/libraries/{library_id}/audiobooks/{book_id}/progress",
                json=data
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to update user progress: {e}")
            return False
    
    def _get_cover_url(self, cover_path: Optional[str]) -> Optional[str]:
        """Construct cover URL from cover path"""
        if not cover_path:
            return None
        return f"{self.base_url}/api/items/{cover_path}/cover"
    
    async def download_chapter(
        self, 
        library_id: str, 
        book_id: str, 
        chapter_id: str,
        output_path: Path
    ) -> bool:
        """Download a chapter audio file"""
        try:
            audio_url = await self.get_chapter_audio_url(library_id, book_id, chapter_id)
            if not audio_url:
                return False
            
            # Use a sync client for downloading
            with httpx.Client(timeout=300.0) as download_client:
                with download_client.stream("GET", audio_url) as response:
                    response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Could add progress callback here
                
                return True
        except Exception as e:
            logger.error(f"Failed to download chapter: {e}")
            return False
