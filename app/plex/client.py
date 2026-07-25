"""
Plex API client
Handles communication with Plex Media Server
"""

import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
import xml.etree.ElementTree as ET

from app.models import Audiobook, Chapter, Library
from app.utils import logger


class PlexClient:
    """Client for Plex API"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Plex-Token": self.token,
                "User-Agent": "Audook/1.0",
                "Accept": "application/json"
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
            response = await self._client.get("/")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def get_libraries(self) -> List[Library]:
        """Get all libraries"""
        try:
            response = await self._client.get("/library/sections")
            response.raise_for_status()
            
            # Plex returns XML
            root = ET.fromstring(response.text)
            
            libraries = []
            for directory in root.findall('.//Directory'):
                lib_type = directory.get("type", "")
                # We're interested in audiobook libraries
                if lib_type in ["audiobook", "artist", "album"]:
                    libraries.append(Library(
                        id=directory.get("key", ""),
                        name=directory.get("title", "Unknown"),
                        source="plex",
                        server_url=self.base_url,
                        server_name=directory.get("name", "")
                    ))
            return libraries
        except Exception as e:
            logger.error(f"Failed to get libraries: {e}")
            return []
    
    async def get_audiobooks(
        self, 
        library_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Audiobook]:
        """Get audiobooks from a library"""
        try:
            params = {
                "type": "10", # Audiobook type
                "limit": limit,
                "offset": offset,
                "sort": "title:asc"
            }
            
            response = await self._client.get(f"/library/sections/{library_id}/all", params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            audiobooks = []
            for video in root.findall('.//Video'):
                audiobook = Audiobook(
                    id=video.get("ratingKey", ""),
                    library_id=library_id,
                    title=video.get("title", "Unknown"),
                    author=self._get_metadata(video, "author"),
                    narrator=self._get_metadata(video, "narrator"),
                    description=video.get("summary", ""),
                    cover=self._get_cover_url(video.get("key")),
                    duration=float(video.get("duration", 0)) / 1000, # Convert ms to s
                    metadata={
                        "year": video.get("year"),
                        "genre": self._get_metadata_list(video, "Genre"),
                        "rating": video.get("rating")
                    },
                    source="plex"
                )
                
                # Get chapters (tracks for audiobooks)
                chapters = []
                for track in video.findall('.//Track'):
                    chapters.append({
                        "id": track.get("id", ""),
                        "title": track.get("title", f"Track {len(chapters) + 1}"),
                        "index": len(chapters),
                        "duration": float(track.get("duration", 0)) / 1000,
                        "audio_file": track.get("key", "")
                    })
                
                if chapters:
                    audiobook.chapters = chapters
                
                audiobooks.append(audiobook)
            
            return audiobooks
        except Exception as e:
            logger.error(f"Failed to get audiobooks: {e}")
            return []
    
    async def get_audiobook(self, library_id: str, book_id: str) -> Optional[Audiobook]:
        """Get a single audiobook by ID"""
        try:
            response = await self._client.get(f"/library/metadata/{book_id}")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            video = root.find('.//Video')
            
            if video is None:
                return None
            
            audiobook = Audiobook(
                id=video.get("ratingKey", ""),
                library_id=library_id,
                title=video.get("title", "Unknown"),
                author=self._get_metadata(video, "author"),
                narrator=self._get_metadata(video, "narrator"),
                description=video.get("summary", ""),
                cover=self._get_cover_url(video.get("key")),
                duration=float(video.get("duration", 0)) / 1000,
                metadata={
                    "year": video.get("year"),
                    "genre": self._get_metadata_list(video, "Genre"),
                    "rating": video.get("rating")
                },
                source="plex"
            )
            
            # Get chapters
            chapters = []
            for track in video.findall('.//Track'):
                chapters.append({
                    "id": track.get("id", ""),
                    "title": track.get("title", f"Track {len(chapters) + 1}"),
                    "index": len(chapters),
                    "duration": float(track.get("duration", 0)) / 1000,
                    "audio_file": track.get("key", "")
                })
            
            audiobook.chapters = chapters
            
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
            # For Plex, we need to get the media info first
            response = await self._client.get(f"/library/metadata/{book_id}")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            video = root.find('.//Video')
            
            if video is None:
                return None
            
            # Find the track with matching ID
            for track in video.findall('.//Track'):
                if track.get("id") == chapter_id:
                    track_key = track.get("key", "")
                    if track_key:
                        # Plex audio streaming URL
                        return f"{self.base_url}{track_key}?download=1"
            
            # If no specific chapter, return the main audio
            media = video.find('.//Media')
            if media is not None:
                part = media.find('.//Part')
                if part is not None:
                    audio_key = part.get("key", "")
                    if audio_key:
                        return f"{self.base_url}{audio_key}?download=1"
            
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
                "query": query,
                "type": "10", # Audiobook
                "limit": limit,
                "sectionID": library_id
            }
            
            response = await self._client.get("/search", params=params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            
            audiobooks = []
            for video in root.findall('.//Video'):
                audiobook = Audiobook(
                    id=video.get("ratingKey", ""),
                    library_id=library_id,
                    title=video.get("title", "Unknown"),
                    author=self._get_metadata(video, "author"),
                    cover=self._get_cover_url(video.get("key")),
                    duration=float(video.get("duration", 0)) / 1000,
                    source="plex"
                )
                audiobooks.append(audiobook)
            
            return audiobooks
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_user_progress(
        self, 
        book_id: str
    ) -> Dict[str, Any]:
        """Get user progress for a book"""
        try:
            # Plex stores progress in the metadata
            response = await self._client.get(f"/library/metadata/{book_id}")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            video = root.find('.//Video')
            
            if video is None:
                return {}
            
            progress = {
                "position": float(video.get("viewOffset", 0)),
                "duration": float(video.get("duration", 0)) / 1000
            }
            
            return progress
        except Exception as e:
            logger.error(f"Failed to get user progress: {e}")
            return {}
    
    async def update_user_progress(
        self, 
        book_id: str,
        position: float
    ) -> bool:
        """Update user progress for a book"""
        try:
            # Plex progress update
            data = f"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
            data += f"<MediaContainer>\n"
            data += f" <Video ratingKey=\"{book_id}\" viewOffset=\"{int(position * 1000)}\" />\n"
            data += f"</MediaContainer>"
            
            response = await self._client.put(
                f"/library/metadata/{book_id}/progress",
                content=data,
                headers={"Content-Type": "application/xml"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to update user progress: {e}")
            return False
    
    def _get_metadata(self, element, tag: str) -> Optional[str]:
        """Get metadata value from element"""
        for child in element:
            if child.tag == tag:
                return child.text
        return None
    
    def _get_metadata_list(self, element, tag: str) -> List[str]:
        """Get list of metadata values from element"""
        result = []
        for child in element:
            if child.tag == tag:
                result.append(child.text or "")
        return result
    
    def _get_cover_url(self, key: Optional[str]) -> Optional[str]:
        """Construct cover URL from key"""
        if not key:
            return None
        return f"{self.base_url}{key}?width=300&height=300"
    
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
                
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"Failed to download chapter: {e}")
            return False
