"""
Library service - manages book data and queries
"""

from typing import List, Optional
from app.database import get_session
from app.database.models import Book, Server, ReadingProgress
from app.models import Audiobook
from app.utils import logger


class LibraryService:
    """Service for managing audiobook library"""

    @staticmethod
    def get_all_books() -> List[Audiobook]:
        """Get all books from database"""
        try:
            session = get_session()
            books = session.query(Book).all()

            audiobooks = []
            for book in books:
                audiobook = LibraryService._db_book_to_audiobook(book)
                audiobooks.append(audiobook)

            session.close()
            logger.info(f"Loaded {len(audiobooks)} books from database")
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to get all books: {e}")
            return []

    @staticmethod
    def get_books_by_server(server_id: str) -> List[Audiobook]:
        """Get books from specific server"""
        try:
            session = get_session()
            books = session.query(Book).filter_by(server_id=server_id).all()

            audiobooks = []
            for book in books:
                audiobook = LibraryService._db_book_to_audiobook(book)
                audiobooks.append(audiobook)

            session.close()
            logger.info(f"Loaded {len(audiobooks)} books from server {server_id}")
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to get books by server: {e}")
            return []

    @staticmethod
    def search_books(query: str) -> List[Audiobook]:
        """Search books by title or author"""
        try:
            session = get_session()
            query_lower = query.lower()

            books = session.query(Book).filter(
                (Book.title.ilike(f"%{query_lower}%")) |
                (Book.author.ilike(f"%{query_lower}%"))
            ).all()

            audiobooks = []
            for book in books:
                audiobook = LibraryService._db_book_to_audiobook(book)
                audiobooks.append(audiobook)

            session.close()
            return audiobooks

        except Exception as e:
            logger.error(f"Failed to search books: {e}")
            return []

    @staticmethod
    def get_book_by_id(book_id: str) -> Optional[Audiobook]:
        """Get specific book by ID"""
        try:
            session = get_session()
            book = session.query(Book).filter_by(id=book_id).first()

            if book:
                audiobook = LibraryService._db_book_to_audiobook(book)
                session.close()
                return audiobook

            session.close()
            return None

        except Exception as e:
            logger.error(f"Failed to get book: {e}")
            return None

    @staticmethod
    def get_reading_progress(book_id: str) -> Optional[dict]:
        """Get reading progress for a book"""
        try:
            session = get_session()
            progress = session.query(ReadingProgress).filter_by(book_id=book_id).first()

            if progress:
                progress_data = {
                    "chapter_index": progress.current_chapter_index,
                    "position_seconds": progress.position_seconds,
                    "progress_percent": progress.progress_percent,
                    "is_finished": progress.is_finished
                }
                session.close()
                return progress_data

            session.close()
            return None

        except Exception as e:
            logger.error(f"Failed to get reading progress: {e}")
            return None

    @staticmethod
    def get_servers() -> List[dict]:
        """Get all configured servers"""
        try:
            session = get_session()
            servers = session.query(Server).filter_by(sync_enabled=True).all()

            server_list = []
            for server in servers:
                server_list.append({
                    "id": server.id,
                    "name": server.name,
                    "type": server.type,
                    "url": server.url,
                    "book_count": len(server.books)
                })

            session.close()
            return server_list

        except Exception as e:
            logger.error(f"Failed to get servers: {e}")
            return []

    @staticmethod
    def _db_book_to_audiobook(db_book: Book) -> Audiobook:
        """Convert database Book to Audiobook model"""
        return Audiobook(
            id=db_book.id,
            library_id=db_book.library_id,
            title=db_book.title,
            author=db_book.author,
            duration=db_book.duration,
            chapters=db_book.chapters or [],
            source=db_book.server.type if db_book.server else "unknown",
            cover=db_book.cover_url,
            narrator=db_book.narrator,
            description=db_book.description,
            metadata=db_book.extra_metadata or {}
        )
