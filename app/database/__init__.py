"""
Database module for Audook
Handles all database operations, models, and session management
"""

from app.database.db import (
    Database,
    init_database,
    get_db,
    get_session,
)

from app.database.models import (
    Base,
    Server,
    Library,
    Book,
    ReadingProgress,
    ReadingHistory,
    SyncLog,
    Device,
    Bookmark,
    AppSettings,
    EqualizerPreset,
    Collection,
)

from app.database.repositories import (
    ServerRepository,
    BookRepository,
    ReadingProgressRepository,
    ReadingHistoryRepository,
    SyncLogRepository,
    BookmarkRepository,
    EqualizerPresetRepository,
    AppSettingsRepository,
    CollectionRepository,
)

__all__ = [
    "Database",
    "init_database",
    "get_db",
    "get_session",
    "Base",
    "Server",
    "Library",
    "Book",
    "ReadingProgress",
    "ReadingHistory",
    "SyncLog",
    "Device",
    "Bookmark",
    "AppSettings",
    "EqualizerPreset",
    "Collection",
    "ServerRepository",
    "BookRepository",
    "ReadingProgressRepository",
    "ReadingHistoryRepository",
    "SyncLogRepository",
    "BookmarkRepository",
    "EqualizerPresetRepository",
    "AppSettingsRepository",
    "CollectionRepository",
]
