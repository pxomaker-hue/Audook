"""
Data Access Objects (Repositories) for database operations
Clean separation between business logic and database
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.models import (
    Server, Library, Book, ReadingProgress, ReadingHistory,
    SyncLog, Device, Bookmark, AppSettings
)
from app.utils import logger


class BaseRepository:
    """Base repository with common operations"""

    def __init__(self, session: Session):
        self.session = session


class ServerRepository(BaseRepository):
    """Operations on Server model"""

    def create(self, server_id: str, type: str, name: str, url: str, api_key: str = None,
               username: str = None, password: str = None) -> Server:
        """Create a new server"""
        server = Server(
            id=server_id, type=type, name=name, url=url,
            api_key=api_key, username=username, password=password
        )
        self.session.add(server)
        self.session.commit()
        logger.info(f"Created server: {name}")
        return server

    def get_all(self) -> List[Server]:
        """Get all servers"""
        return self.session.query(Server).all()

    def get_by_id(self, server_id: str) -> Optional[Server]:
        """Get server by ID"""
        return self.session.query(Server).filter_by(id=server_id).first()

    def update_sync_timestamp(self, server_id: str):
        """Update last sync timestamp"""
        server = self.get_by_id(server_id)
        if server:
            server.last_sync = datetime.utcnow()
            self.session.commit()

    def delete(self, server_id: str):
        """Delete a server"""
        server = self.get_by_id(server_id)
        if server:
            self.session.delete(server)
            self.session.commit()
            logger.info(f"Deleted server: {server.name}")


class BookRepository(BaseRepository):
    """Operations on Book model"""

    # Fields inside extra_metadata (as opposed to real columns) that can be
    # locked against being overwritten by a scan - see `manual_overrides`.
    _EXTRA_METADATA_LOCKABLE_FIELDS = ("author_bio", "author_photo", "series")

    def create(self, book_id: str, server_id: str, library_id: str, title: str,
               author: str = None, narrator: str = None, description: str = None, duration: float = 0.0,
               chapters: dict = None, cover_url: str = None, extra_metadata: dict = None) -> Book:
        """Create or update a book from a scan (idempotent across re-scans).

        Fields the user has manually edited (tracked via
        extra_metadata.manual_overrides) are preserved instead of being
        overwritten by the freshly-scanned source data.
        """
        book = self.get_by_id(book_id)
        existing_extra = (book.extra_metadata or {}) if book else {}
        overrides = set(existing_extra.get("manual_overrides") or [])

        if book is None:
            book = Book(id=book_id)
            self.session.add(book)

        book.server_id = server_id
        book.library_id = library_id
        if "title" not in overrides:
            book.title = title
        if "author" not in overrides:
            book.author = author
        if "narrator" not in overrides:
            book.narrator = narrator
        if "description" not in overrides:
            book.description = description
        book.duration = duration
        book.chapters = chapters or []
        if "cover_url" not in overrides:
            book.cover_url = cover_url

        new_extra = dict(extra_metadata or {})
        for field in self._EXTRA_METADATA_LOCKABLE_FIELDS:
            if field in overrides and field in existing_extra:
                new_extra[field] = existing_extra[field]
        if overrides:
            new_extra["manual_overrides"] = list(overrides)
        book.extra_metadata = new_extra

        self.session.commit()
        return book

    def update_fields(self, book_id: str, fields: Dict[str, Any], lock: bool = True) -> Optional[Book]:
        """Manually update specific fields on a book, optionally locking them
        against being overwritten by a future scan."""
        book = self.get_by_id(book_id)
        if not book:
            return None

        extra = dict(book.extra_metadata or {})
        overrides = set(extra.get("manual_overrides") or [])

        column_fields = ("title", "author", "narrator", "description", "cover_url")
        for key, value in fields.items():
            if key in column_fields:
                setattr(book, key, value)
                if lock:
                    overrides.add(key)
            elif key in self._EXTRA_METADATA_LOCKABLE_FIELDS:
                extra[key] = value
                if lock:
                    overrides.add(key)

        if overrides:
            extra["manual_overrides"] = list(overrides)
        book.extra_metadata = extra

        self.session.commit()
        return book

    def get_by_id(self, book_id: str) -> Optional[Book]:
        """Get book by ID"""
        return self.session.query(Book).filter_by(id=book_id).first()

    def get_by_library(self, library_id: str) -> List[Book]:
        """Get all books in a library"""
        return self.session.query(Book).filter_by(library_id=library_id).all()

    def get_by_server(self, server_id: str) -> List[Book]:
        """Get all books from a server"""
        return self.session.query(Book).filter_by(server_id=server_id).all()

    def get_by_author(self, author: str) -> List[Book]:
        """Get all books by an exact author string"""
        return self.session.query(Book).filter_by(author=author).all()

    def search(self, query: str) -> List[Book]:
        """Search books by title or author"""
        query_lower = query.lower()
        return self.session.query(Book).filter(
            (Book.title.ilike(f"%{query_lower}%")) |
            (Book.author.ilike(f"%{query_lower}%"))
        ).all()

    def delete(self, book_id: str):
        """Delete a book"""
        book = self.get_by_id(book_id)
        if book:
            self.session.delete(book)
            self.session.commit()


class ReadingProgressRepository(BaseRepository):
    """Operations on ReadingProgress model"""

    def get_or_create(self, book_id: str) -> ReadingProgress:
        """Get or create reading progress for a book"""
        progress = self.session.query(ReadingProgress).filter_by(book_id=book_id).first()
        if not progress:
            progress = ReadingProgress(book_id=book_id)
            self.session.add(progress)
            self.session.commit()
        return progress

    def update_progress(self, book_id: str, chapter_index: int, position: float, percent: float):
        """Update reading progress"""
        progress = self.get_or_create(book_id)
        progress.current_chapter_index = chapter_index
        progress.position_seconds = position
        progress.progress_percent = percent
        progress.last_updated = datetime.utcnow()
        self.session.commit()

    def mark_finished(self, book_id: str):
        """Mark a book as finished"""
        progress = self.get_or_create(book_id)
        progress.is_finished = True
        progress.finished_at = datetime.utcnow()
        progress.progress_percent = 100.0
        self.session.commit()

    def get_current_chapter(self, book_id: str) -> int:
        """Get current chapter index"""
        progress = self.session.query(ReadingProgress).filter_by(book_id=book_id).first()
        return progress.current_chapter_index if progress else 0

    def get_current_position(self, book_id: str) -> float:
        """Get current position in seconds"""
        progress = self.session.query(ReadingProgress).filter_by(book_id=book_id).first()
        return progress.position_seconds if progress else 0.0

    def delete(self, book_id: str) -> bool:
        """Reset (delete) the reading progress for a single book"""
        progress = self.session.query(ReadingProgress).filter_by(book_id=book_id).first()
        if not progress:
            return False
        self.session.delete(progress)
        self.session.commit()
        return True

    def delete_all(self) -> int:
        """Reset (delete) all reading progress, returns the number deleted"""
        count = self.session.query(ReadingProgress).delete()
        self.session.commit()
        return count

    def get_in_progress_map(self) -> dict:
        """Get {book_id: {percent, chapter_index}} for books that have been
        started but not finished"""
        rows = self.session.query(ReadingProgress).filter(
            ReadingProgress.progress_percent > 0,
            ReadingProgress.is_finished == False  # noqa: E712
        ).all()
        return {
            row.book_id: {"percent": row.progress_percent, "chapter_index": row.current_chapter_index}
            for row in rows
        }


class ReadingHistoryRepository(BaseRepository):
    """Operations on ReadingHistory model"""

    def create_session(self, book_id: str, start_pos: float, start_chapter: int, device_id: str = None) -> ReadingHistory:
        """Create a new reading session"""
        session = ReadingHistory(
            book_id=book_id,
            session_start=datetime.utcnow(),
            session_end=datetime.utcnow(),
            start_position=start_pos,
            start_chapter=start_chapter,
            device_id=device_id
        )
        self.session.add(session)
        self.session.commit()
        return session

    def end_session(self, history_id: int, end_pos: float, end_chapter: int):
        """End a reading session"""
        history = self.session.query(ReadingHistory).filter_by(id=history_id).first()
        if history:
            history.session_end = datetime.utcnow()
            history.end_position = end_pos
            history.end_chapter = end_chapter
            history.duration_seconds = (history.session_end - history.session_start).total_seconds()
            self.session.commit()

    def get_by_book(self, book_id: str, limit: int = 50) -> List[ReadingHistory]:
        """Get reading history for a book"""
        return self.session.query(ReadingHistory).filter_by(book_id=book_id).order_by(
            ReadingHistory.session_start.desc()
        ).limit(limit).all()

    def get_recent(self, limit: int = 10) -> List[ReadingHistory]:
        """Get recent reading sessions"""
        return self.session.query(ReadingHistory).order_by(
            ReadingHistory.session_start.desc()
        ).limit(limit).all()

    def delete(self, history_id: int) -> bool:
        """Delete a single reading history entry"""
        history = self.session.query(ReadingHistory).filter_by(id=history_id).first()
        if not history:
            return False
        self.session.delete(history)
        self.session.commit()
        return True

    def delete_all(self) -> int:
        """Delete all reading history entries, returns the number deleted"""
        count = self.session.query(ReadingHistory).delete()
        self.session.commit()
        return count


class SyncLogRepository(BaseRepository):
    """Operations on SyncLog model"""

    def create(self, server_id: str, sync_type: str) -> SyncLog:
        """Create a new sync log entry"""
        log = SyncLog(server_id=server_id, sync_type=sync_type)
        self.session.add(log)
        self.session.commit()
        return log

    def mark_success(self, log_id: int):
        """Mark sync as successful"""
        log = self.session.query(SyncLog).filter_by(id=log_id).first()
        if log:
            log.status = "success"
            log.completed_at = datetime.utcnow()
            log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
            self.session.commit()

    def mark_failed(self, log_id: int, error_message: str):
        """Mark sync as failed"""
        log = self.session.query(SyncLog).filter_by(id=log_id).first()
        if log:
            log.status = "failed"
            log.error_message = error_message
            log.completed_at = datetime.utcnow()
            log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
            self.session.commit()

    def get_recent_logs(self, server_id: str, limit: int = 20) -> List[SyncLog]:
        """Get recent sync logs for a server"""
        return self.session.query(SyncLog).filter_by(server_id=server_id).order_by(
            SyncLog.started_at.desc()
        ).limit(limit).all()


class BookmarkRepository(BaseRepository):
    """Operations on Bookmark model"""

    def create(self, book_id: str, chapter_index: int, position: float, title: str = None) -> Bookmark:
        """Create a new bookmark"""
        bookmark = Bookmark(
            book_id=book_id,
            chapter_index=chapter_index,
            position_seconds=position,
            title=title
        )
        self.session.add(bookmark)
        self.session.commit()
        return bookmark

    def get_by_book(self, book_id: str) -> List[Bookmark]:
        """Get all bookmarks for a book"""
        return self.session.query(Bookmark).filter_by(book_id=book_id).order_by(
            Bookmark.chapter_index.asc(), Bookmark.position_seconds.asc()
        ).all()

    def delete(self, bookmark_id: int):
        """Delete a bookmark"""
        bookmark = self.session.query(Bookmark).filter_by(id=bookmark_id).first()
        if bookmark:
            self.session.delete(bookmark)
            self.session.commit()

    def get_by_id(self, bookmark_id: int) -> Optional[Bookmark]:
        """Get a single bookmark"""
        return self.session.query(Bookmark).filter_by(id=bookmark_id).first()

    def get_book_ids_with_bookmarks(self) -> set:
        """Get the set of book_ids that have at least one bookmark (for the
        library-wide badge, independent of - and not cleared by - reading
        progress resets)"""
        rows = self.session.query(Bookmark.book_id).distinct().all()
        return {row[0] for row in rows}
