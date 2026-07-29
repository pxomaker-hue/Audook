"""
Data Access Objects (Repositories) for database operations
Clean separation between business logic and database
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from app.database.models import (
    Server, Library, Book, ReadingProgress, ReadingHistory,
    SyncLog, Device, Bookmark, AppSettings, EqualizerPreset, Collection
)
from app.utils import logger

# Sentinel for optional repository params where None is a valid value to set
# (e.g. "clear this field") and must be distinguishable from "not provided".
_UNSET = object()


class BaseRepository:
    """Base repository with common operations"""

    def __init__(self, session: Session):
        self.session = session


class ServerRepository(BaseRepository):
    """Operations on Server model"""

    def create(self, server_id: str, type: str, name: str, url: str, api_key: str = None,
               username: str = None, password: str = None, remote_url: str = None) -> Server:
        """Create a new server"""
        server = Server(
            id=server_id, type=type, name=name, url=url,
            api_key=api_key, username=username, password=password,
            remote_url=remote_url
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

    def set_remote_access(self, server_id: str, remote_url=_UNSET, use_remote: bool = None) -> Optional[Server]:
        """Update the remote (Audiobookshelf) address and/or which one
        (local `url` vs `remote_url`) is currently active. remote_url left
        at its default (_UNSET) leaves the stored value untouched; passing
        None/'' explicitly clears it."""
        server = self.get_by_id(server_id)
        if not server:
            return None
        if remote_url is not _UNSET:
            server.remote_url = remote_url or None
        if use_remote is not None:
            server.use_remote = use_remote
        self.session.commit()
        return server

    def set_hidden(self, server_id: str, hidden: bool) -> Optional[Server]:
        """Hide/show this server's books in the library views, without
        touching any synced data - see Book queries filtering on this."""
        server = self.get_by_id(server_id)
        if not server:
            return None
        server.hidden = hidden
        self.session.commit()
        return server

    def get_hidden_server_ids(self) -> set:
        """Server ids currently hidden - used to filter book listings."""
        rows = self.session.query(Server.id).filter_by(hidden=True).all()
        return {row[0] for row in rows}

    @staticmethod
    def active_url(server: Server) -> str:
        """The address to actually connect to right now, honoring the
        local/remote toggle - falls back to the local url if "remote" is
        selected but none was ever set."""
        if server.use_remote and server.remote_url:
            return server.remote_url
        return server.url

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
    _EXTRA_METADATA_LOCKABLE_FIELDS = ("author_bio", "author_photo", "series", "series_sequence", "genre")

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
        # Not a scanned metadata field, so it isn't part of the
        # manual_overrides system above - always carry it forward so a
        # rescan can't silently re-seed progress the user explicitly
        # dismissed (see the /progress DELETE route and
        # scanner.py's _seed_remote_progress_if_new).
        if existing_extra.get("progress_dismissed"):
            new_extra["progress_dismissed"] = True
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

    def update_chapter_titles(self, book_id: str, titles: List[str]) -> Optional[Book]:
        """Replace just the "title" of each chapter, keeping audio_file/
        duration/index/id untouched - used to swap in real chapter names
        (e.g. from Audible) over generic/duplicate ones from the original
        source, without touching anything about how the chapters actually
        play. Only applies if the title count matches the chapter count
        exactly - a mismatch means the source's chapter boundaries don't
        line up with ours, and titles would land on the wrong chapter."""
        book = self.get_by_id(book_id)
        if not book or not book.chapters or len(titles) != len(book.chapters):
            return None

        updated = [{**chapter, "title": title} for chapter, title in zip(book.chapters, titles)]
        book.chapters = updated
        self.session.commit()
        return book

    def lock_fields(self, book_id: str, field_names: List[str]) -> Optional[Book]:
        """Lock fields against being overwritten by a future scan or online
        match/replace, without changing their current value - lets the user
        freely lock a field they're happy with instead of only ever getting
        locked as a side effect of editing/saving it."""
        book = self.get_by_id(book_id)
        if not book:
            return None

        extra = dict(book.extra_metadata or {})
        overrides = set(extra.get("manual_overrides") or [])
        overrides.update(field_names)
        extra["manual_overrides"] = list(overrides)
        book.extra_metadata = extra

        self.session.commit()
        return book

    def unlock_fields(self, book_id: str, field_names: List[str]) -> Optional[Book]:
        """Remove fields from manual_overrides so a future scan or online
        match/replace is free to overwrite them again - the counterpart to
        the automatic locking that happens on manual edit/match."""
        book = self.get_by_id(book_id)
        if not book:
            return None

        extra = dict(book.extra_metadata or {})
        overrides = set(extra.get("manual_overrides") or [])
        overrides.difference_update(field_names)

        if overrides:
            extra["manual_overrides"] = list(overrides)
        else:
            extra.pop("manual_overrides", None)
        book.extra_metadata = extra

        self.session.commit()
        return book

    def get_by_id(self, book_id: str) -> Optional[Book]:
        """Get book by ID"""
        return self.session.query(Book).filter_by(id=book_id).first()

    @staticmethod
    def _normalize_for_dedup(text: Optional[str]) -> str:
        """Loose normalization for title/author dedup matching across
        sources (accent/case/punctuation-insensitive) - "Le Baptême du feu"
        from Audiobookshelf and a locally-ripped folder named similarly
        should be recognized as the same book."""
        import unicodedata
        import re
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9]+", "", text.lower())
        return text

    @staticmethod
    def _primary_author(author: Optional[str]) -> str:
        """First author only, normalized - local file tags often append
        narrator/translator credits after a comma (e.g. "Andrzej Sapkowski,
        Lydia Cantin-Waleryszak - traducteur") that a server-sourced author
        field won't have, which would otherwise defeat dedup matching."""
        if not author:
            return ""
        return author.split(",")[0]

    def find_existing_from_other_source(self, title: str, author: str, exclude_server_id: str) -> Optional[Book]:
        """A book with a matching (normalized) title+author already scanned
        from a *different* server - used so a local-folder scan doesn't
        create a duplicate entry for a book already present via Plex/
        Audiobookshelf with richer metadata (series, tags, etc)."""
        target_title = self._normalize_for_dedup(title)
        target_author = self._normalize_for_dedup(self._primary_author(author))
        if not target_title:
            return None

        candidates = self.session.query(Book).filter(Book.server_id != exclude_server_id).all()
        for candidate in candidates:
            if (self._normalize_for_dedup(candidate.title) == target_title
                    and self._normalize_for_dedup(self._primary_author(candidate.author)) == target_author):
                return candidate
        return None

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

    def get_noise_reduction_status(self, book_id: str) -> str:
        """'idle' | 'processing' | 'done' | 'error' - see
        app/utils/noise_reduction.py and POST /api/books/<id>/clean-audio."""
        book = self.get_by_id(book_id)
        if not book or not book.extra_metadata:
            return 'idle'
        return book.extra_metadata.get('noise_reduction_status', 'idle')

    def set_noise_reduction_status(self, book_id: str, status: str):
        book = self.get_by_id(book_id)
        if not book:
            return
        extra = dict(book.extra_metadata or {})
        extra['noise_reduction_status'] = status
        book.extra_metadata = extra
        self.session.commit()

    def get_cleaned_chapter_path(self, book_id: str, chapter_index: int) -> Optional[str]:
        book = self.get_by_id(book_id)
        if not book or not book.extra_metadata:
            return None
        # Respect the user's choice to revert to the original source (see
        # set_use_cleaned_audio) even though the cleaned copy is still
        # cached - flipping this back on later doesn't require re-cleaning.
        if not book.extra_metadata.get('use_cleaned_audio', True):
            return None
        paths = book.extra_metadata.get('cleaned_chapter_paths') or {}
        return paths.get(str(chapter_index))

    def get_use_cleaned_audio(self, book_id: str) -> bool:
        book = self.get_by_id(book_id)
        if not book or not book.extra_metadata:
            return True
        return book.extra_metadata.get('use_cleaned_audio', True)

    def set_use_cleaned_audio(self, book_id: str, enabled: bool):
        """Switch a book back to its original audio (enabled=False) or back
        to the cleaned version (enabled=True), without touching the cached
        cleaned files either way - see clean-audio's 'Nettoyer à nouveau' vs
        just re-toggling this."""
        book = self.get_by_id(book_id)
        if not book:
            return
        extra = dict(book.extra_metadata or {})
        extra['use_cleaned_audio'] = enabled
        book.extra_metadata = extra
        self.session.commit()

    def set_cleaned_chapter_path(self, book_id: str, chapter_index: int, path: str):
        book = self.get_by_id(book_id)
        if not book:
            return
        extra = dict(book.extra_metadata or {})
        paths = dict(extra.get('cleaned_chapter_paths') or {})
        paths[str(chapter_index)] = path
        extra['cleaned_chapter_paths'] = paths
        book.extra_metadata = extra
        self.session.commit()

    def get_loudness_gain(self, book_id: str) -> Optional[float]:
        """dB gain previously measured for this book (see app.utils.audio_loudness),
        or None if it hasn't been analyzed yet."""
        book = self.get_by_id(book_id)
        if not book or not book.extra_metadata:
            return None
        gain = book.extra_metadata.get("loudness_gain_db")
        return float(gain) if gain is not None else None

    def set_loudness_gain(self, book_id: str, gain_db: float):
        """Cache a measured loudness gain so it's only computed once per book."""
        book = self.get_by_id(book_id)
        if not book:
            return
        extra = dict(book.extra_metadata or {})
        extra["loudness_gain_db"] = gain_db
        book.extra_metadata = extra
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
        self.set_finished(book_id, True)

    def set_finished(self, book_id: str, finished: bool) -> ReadingProgress:
        """Manually set/unset a book's finished status"""
        progress = self.get_or_create(book_id)
        progress.is_finished = finished
        progress.finished_at = datetime.utcnow() if finished else None
        if finished:
            progress.progress_percent = 100.0
        self.session.commit()
        return progress

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

    def get_finished_book_ids(self) -> set:
        """Get the set of book_ids marked as finished (manually or automatically)"""
        rows = self.session.query(ReadingProgress.book_id).filter(
            ReadingProgress.is_finished == True  # noqa: E712
        ).all()
        return {row[0] for row in rows}

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


class EqualizerPresetRepository(BaseRepository):
    """Operations on EqualizerPreset model"""

    # (id, name, bands, preamp) - bands are 10 floats for 31Hz..16kHz, seeded
    # once on first use. "Voix" cuts rumble/mud and lifts the 1-4kHz presence
    # range where speech intelligibility lives, with a slight treble rolloff
    # to tame sibilance/hiss on older or amateur recordings - the rest are the
    # classic genre-style curves (kept moderate since this is spoken-word
    # audio, not music - a subtle shape rather than the usual aggressive
    # music-EQ swings).
    BUILTIN_PRESETS = [
        ("builtin-flat", "Flat", [0.0] * 10, 0.0),
        ("builtin-voice", "Voix", [-4.0, -3.0, -1.0, 0.0, 1.0, 2.0, 3.0, 2.0, 0.0, -1.0], 1.5),
        ("builtin-rock", "Rock", [4.0, 3.0, 1.0, -1.0, -2.0, 0.0, 2.0, 3.0, 4.0, 4.0], 1.0),
        ("builtin-pop", "Pop", [-1.0, 0.0, 2.0, 3.0, 3.0, 2.0, 0.0, -1.0, -1.0, -2.0], 0.5),
        ("builtin-jazz", "Jazz", [3.0, 2.0, 1.0, 0.0, -1.0, 0.0, 1.0, 2.0, 2.0, 3.0], 0.5),
        ("builtin-classical", "Classique", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, -1.0, -2.0, -3.0], 0.0),
        ("builtin-bass-boost", "Boost Basses", [7.0, 6.0, 5.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0], 2.0),
        ("builtin-treble-boost", "Boost Aigus", [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 3.0, 5.0, 6.0, 7.0], 2.0),
    ]

    def ensure_builtins(self):
        """Seed the built-in presets, adding any that don't already exist yet
        (per-id, not just "any builtin exists") so growing this list later -
        as happened here - backfills existing databases instead of silently
        skipping them."""
        existing_ids = {
            row[0] for row in self.session.query(EqualizerPreset.id).filter_by(is_builtin=True).all()
        }
        added = False
        for i, (preset_id, name, bands, preamp) in enumerate(self.BUILTIN_PRESETS):
            if preset_id in existing_ids:
                continue
            self.session.add(EqualizerPreset(
                id=preset_id, name=name, bands=bands, preamp=preamp,
                is_builtin=True, position=i
            ))
            added = True
        if added:
            self.session.commit()

    def get_all(self) -> List[EqualizerPreset]:
        """All presets (built-in first), in cycling order"""
        return self.session.query(EqualizerPreset).order_by(EqualizerPreset.position).all()

    def get_by_id(self, preset_id: str) -> Optional[EqualizerPreset]:
        return self.session.query(EqualizerPreset).filter_by(id=preset_id).first()

    def create(self, name: str, bands: List[float], preamp: float = 0.0) -> EqualizerPreset:
        max_position = self.session.query(EqualizerPreset).count()
        preset = EqualizerPreset(
            id=str(uuid.uuid4()),
            name=name,
            bands=bands,
            preamp=preamp,
            is_builtin=False,
            position=max_position
        )
        self.session.add(preset)
        self.session.commit()
        return preset

    def update(self, preset_id: str, name: str = None, bands: List[float] = None,
               preamp: float = None) -> Optional[EqualizerPreset]:
        """Update a custom preset. Built-ins are read-only - returns None."""
        preset = self.get_by_id(preset_id)
        if not preset or preset.is_builtin:
            return None
        if name is not None:
            preset.name = name
        if bands is not None:
            preset.bands = bands
        if preamp is not None:
            preset.preamp = preamp
        self.session.commit()
        return preset

    def delete(self, preset_id: str) -> bool:
        """Delete a custom preset. Built-ins are protected - returns False."""
        preset = self.get_by_id(preset_id)
        if not preset or preset.is_builtin:
            return False
        self.session.delete(preset)
        self.session.commit()
        return True


class AppSettingsRepository(BaseRepository):
    """Simple key-value store for small app-wide preferences (active
    equalizer preset, normalization toggle, ...) that don't warrant their
    own dedicated table/columns."""

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.session.query(AppSettings).filter_by(key=key).first()
        return row.value if row else default

    def set(self, key: str, value: str):
        row = self.session.query(AppSettings).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            row = AppSettings(key=key, value=value)
            self.session.add(row)
        self.session.commit()


class CollectionRepository(BaseRepository):
    """Operations on Collection model - user-created custom groupings of
    books, membership stored as a plain JSON list of book ids."""

    def get_all(self) -> List[Collection]:
        return self.session.query(Collection).order_by(Collection.position, Collection.created_at).all()

    def get_by_id(self, collection_id: str) -> Optional[Collection]:
        return self.session.query(Collection).filter_by(id=collection_id).first()

    def create(self, name: str) -> Collection:
        max_position = self.session.query(Collection).count()
        collection = Collection(id=str(uuid.uuid4()), name=name, book_ids=[], position=max_position)
        self.session.add(collection)
        self.session.commit()
        return collection

    def rename(self, collection_id: str, name: str) -> Optional[Collection]:
        collection = self.get_by_id(collection_id)
        if not collection:
            return None
        collection.name = name
        self.session.commit()
        return collection

    def delete(self, collection_id: str) -> bool:
        collection = self.get_by_id(collection_id)
        if not collection:
            return False
        self.session.delete(collection)
        self.session.commit()
        return True

    def add_book(self, collection_id: str, book_id: str) -> Optional[Collection]:
        collection = self.get_by_id(collection_id)
        if not collection:
            return None
        book_ids = list(collection.book_ids or [])
        if book_id not in book_ids:
            book_ids.append(book_id)
            collection.book_ids = book_ids
            self.session.commit()
        return collection

    def remove_book(self, collection_id: str, book_id: str) -> Optional[Collection]:
        collection = self.get_by_id(collection_id)
        if not collection:
            return None
        book_ids = [b for b in (collection.book_ids or []) if b != book_id]
        collection.book_ids = book_ids
        self.session.commit()
        return collection
