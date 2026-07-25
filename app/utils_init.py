"""
Initialize application with test data if database is empty
"""

from app.database import get_session, ServerRepository, BookRepository
from app.utils import logger


def ensure_test_data():
    """Create test data if database is empty"""
    try:
        session = get_session()

        # Check if we already have books
        from app.database.models import Book
        existing_books = session.query(Book).count()

        if existing_books > 0:
            session.close()
            return

        logger.info("Creating test data...")

        # Create test server
        server_repo = ServerRepository(session)
        server = server_repo.create(
            server_id="test_local",
            type="local",
            name="Local Library",
            url="http://localhost:8000"
        )

        # Create test books
        book_repo = BookRepository(session)

        test_books = [
            {
                "id": "gatsby",
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "narrator": "Jake Gyllenhaal",
                "duration": 9.5 * 3600,
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Chapter 1",
                        "index": 0,
                        "duration": 600.0,
                        "audio_file": "http://localhost:8000/gatsby/ch1.m4b"
                    }
                ]
            },
            {
                "id": "hobbit",
                "title": "The Hobbit",
                "author": "J.R.R. Tolkien",
                "narrator": "Rob Inglis",
                "duration": 11 * 3600,
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Chapter 1",
                        "index": 0,
                        "duration": 700.0,
                        "audio_file": "http://localhost:8000/hobbit/ch1.m4b"
                    }
                ]
            },
            {
                "id": "pride",
                "title": "Pride and Prejudice",
                "author": "Jane Austen",
                "narrator": "Rosamund Pike",
                "duration": 12 * 3600,
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Chapter 1",
                        "index": 0,
                        "duration": 650.0,
                        "audio_file": "http://localhost:8000/pride/ch1.m4b"
                    }
                ]
            }
        ]

        for book_data in test_books:
            book_repo.create(
                book_id=book_data["id"],
                server_id=server.id,
                library_id="local",
                title=book_data["title"],
                author=book_data["author"],
                narrator=book_data.get("narrator"),
                duration=book_data["duration"],
                chapters=book_data["chapters"]
            )
            logger.info(f"Created test book: {book_data['title']}")

        session.close()
        logger.info("Test data created successfully")

    except Exception as e:
        logger.error(f"Failed to create test data: {e}")
