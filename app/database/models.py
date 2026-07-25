"""
SQLAlchemy models for Audook
Complete database schema for audiobook management, progress tracking, and sync
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Server(Base):
    """Configured Plex or Audiobookshelf server"""
    __tablename__ = "servers"

    id = Column(String(50), primary_key=True)
    type = Column(String(20), nullable=False)  # "plex" or "audiobookshelf"
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    api_key = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    # Sync info
    last_sync = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    libraries = relationship("Library", back_populates="server", cascade="all, delete-orphan")
    books = relationship("Book", back_populates="server", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="server", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Server {self.name} ({self.type})>"


class Library(Base):
    """Book library from a server"""
    __tablename__ = "libraries"

    id = Column(String(100), primary_key=True)
    server_id = Column(String(50), ForeignKey("servers.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source = Column(String(20), nullable=False)  # "plex", "audiobookshelf", "local"

    # Sync info
    last_scan = Column(DateTime, nullable=True)
    scan_enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    server = relationship("Server", back_populates="libraries")
    books = relationship("Book", back_populates="library", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Library {self.name}>"


class Book(Base):
    """Audiobook metadata"""
    __tablename__ = "books"

    id = Column(String(100), primary_key=True)
    server_id = Column(String(50), ForeignKey("servers.id"), nullable=False)
    library_id = Column(String(100), ForeignKey("libraries.id"), nullable=False)

    # Book info
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    narrator = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cover_url = Column(String(500), nullable=True)

    # Audio info
    duration = Column(Float, default=0.0)  # Total duration in seconds
    chapters_count = Column(Integer, default=0)

    # Chapters data (JSON)
    chapters = Column(JSON, nullable=True)  # Array of chapter objects

    # Metadata
    metadata = Column(JSON, nullable=True)  # Extra metadata from server

    # Sync info
    last_sync = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    server = relationship("Server", back_populates="books")
    library = relationship("Library", back_populates="books")
    progress = relationship("ReadingProgress", back_populates="book", uselist=False, cascade="all, delete-orphan")
    history = relationship("ReadingHistory", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Book {self.title}>"


class ReadingProgress(Base):
    """Current reading progress for a book"""
    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True)
    book_id = Column(String(100), ForeignKey("books.id"), nullable=False, unique=True)

    # Progress info
    current_chapter_index = Column(Integer, default=0)  # Chapter number (0-indexed)
    position_seconds = Column(Float, default=0.0)  # Position in current chapter
    progress_percent = Column(Float, default=0.0)  # Overall progress (0-100)

    # Status
    is_finished = Column(Boolean, default=False)
    finished_at = Column(DateTime, nullable=True)

    # Sync status
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_with_server = Column(Boolean, default=False)
    last_synced = Column(DateTime, nullable=True)

    # Relationships
    book = relationship("Book", back_populates="progress")

    def __repr__(self):
        return f"<ReadingProgress {self.book_id}: {self.progress_percent}%>"


class ReadingHistory(Base):
    """Complete history of reading sessions"""
    __tablename__ = "reading_history"

    id = Column(Integer, primary_key=True)
    book_id = Column(String(100), ForeignKey("books.id"), nullable=False)

    # Session info
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=False)
    duration_seconds = Column(Float)  # How long listened in this session

    # Position at start/end of session
    start_position = Column(Float)
    end_position = Column(Float)
    start_chapter = Column(Integer)
    end_chapter = Column(Integer)

    # Device info
    device_id = Column(String(50), nullable=True)

    # Relationships
    book = relationship("Book", back_populates="history")

    def __repr__(self):
        return f"<ReadingHistory {self.book_id} - {self.duration_seconds}s>"


class SyncLog(Base):
    """Log of all sync operations"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    server_id = Column(String(50), ForeignKey("servers.id"), nullable=False)

    # Sync info
    sync_type = Column(String(50), nullable=False)  # "full", "progress", "bookmark", etc
    status = Column(String(20), default="pending")  # "pending", "success", "failed"

    # Details
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Relationships
    server = relationship("Server", back_populates="sync_logs")

    def __repr__(self):
        return f"<SyncLog {self.sync_type}: {self.status}>"


class Device(Base):
    """Device for multi-device sync"""
    __tablename__ = "devices"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    device_type = Column(String(20), default="windows")  # "windows", "mac", "android", etc

    # Sync settings
    sync_enabled = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)

    # Device info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Device {self.name}>"


class Bookmark(Base):
    """User bookmarks in audiobooks"""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    book_id = Column(String(100), ForeignKey("books.id"), nullable=False)

    # Bookmark info
    chapter_index = Column(Integer, nullable=False)
    position_seconds = Column(Float, nullable=False)
    title = Column(String(255), nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Bookmark {self.book_id}: {self.position_seconds}s>"


class AppSettings(Base):
    """Application settings and preferences"""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings {self.key}>"
