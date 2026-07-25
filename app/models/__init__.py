"""
Data models for Audook
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path


class Bookmark(BaseModel):
    """Bookmark model for saving positions in audiobooks"""
    book_id: str
    library_id: str
    chapter_id: Optional[str] = None
    position: float  # Position in seconds
    timestamp: datetime = Field(default_factory=datetime.now)
    title: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlaybackState(BaseModel):
    """Current playback state"""
    book_id: str
    library_id: str
    chapter_id: Optional[str] = None
    position: float = 0.0
    is_playing: bool = False
    speed: float = 1.0
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Audiobook(BaseModel):
    """Audiobook model"""
    id: str
    library_id: str
    title: str
    author: str
    narrator: Optional[str] = None
    description: Optional[str] = None
    cover: Optional[str] = None
    duration: float = 0.0
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "audiobookshelf"  # or "plex"
    
    # Local cache info
    local_path: Optional[Path] = None
    is_downloaded: bool = False
    
    @property
    def display_title(self) -> str:
        return f"{self.title} - {self.author}"


class Chapter(BaseModel):
    """Chapter model"""
    id: str
    title: str
    index: int
    duration: float
    start: float = 0.0
    audio_file: str
    
    @property
    def display_title(self) -> str:
        return f"{self.index + 1}. {self.title}"


class Library(BaseModel):
    """Library model"""
    id: str
    name: str
    source: str  # "audiobookshelf" or "plex"
    server_url: str
    server_name: Optional[str] = None
    
    # Connection info (not serialized)
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    class Config:
        json_encoders = {
            Path: lambda v: str(v)
        }


class ServerConfig(BaseModel):
    """Server configuration"""
    id: str
    name: str
    type: str  # "audiobookshelf" or "plex"
    url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    libraries: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            Path: lambda v: str(v)
        }


class AppConfig(BaseModel):
    """Application configuration"""
    servers: List[ServerConfig] = Field(default_factory=list)
    current_server_id: Optional[str] = None
    current_library_id: Optional[str] = None
    theme: str = "dark"
    playback_speed: float = 1.0
    volume: float = 0.8
    remember_position: bool = True
    sync_enabled: bool = True
    download_quality: str = "high"
    
    class Config:
        json_encoders = {
            Path: lambda v: str(v)
        }
