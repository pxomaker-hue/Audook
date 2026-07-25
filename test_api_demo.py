#!/usr/bin/env python3
"""
Demo: API Client architecture for Plex and Audiobookshelf
Shows the structure without requiring actual servers
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database, get_session, ServerRepository, BookRepository
from app.database.models import Server, Book


def demo_audiobookshelf_structure():
    """Demonstrate Audiobookshelf client response structure"""
    print("=" * 60)
    print("Audiobookshelf API Response Structure")
    print("=" * 60)
    print()

    print("Sample audiobook data from Audiobookshelf API:")
    print()

    audiobook_sample = {
        "id": "abs_book_123",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "narrator": "Jake Gyllenhaal",
        "description": "A classic novel of the Jazz Age",
        "cover_url": "http://abs-server/api/books/book_123/cover",
        "duration": 9.5 * 3600,  # 9.5 hours in seconds
        "chapters": [
            {
                "id": "track_1",
                "title": "Chapter 1",
                "index": 0,
                "duration": 1200.0,
                "audio_file": "http://abs-server/api/books/book_123/stream"
            },
            {
                "id": "track_2",
                "title": "Chapter 2",
                "index": 1,
                "duration": 1100.0,
                "audio_file": "http://abs-server/api/books/book_123/stream"
            }
        ]
    }

    print(f"Title: {audiobook_sample['title']}")
    print(f"Author: {audiobook_sample['author']}")
    print(f"Narrator: {audiobook_sample['narrator']}")
    print(f"Chapters: {len(audiobook_sample['chapters'])}")
    print(f"Duration: {audiobook_sample['duration'] / 3600:.1f} hours")
    print()


def demo_plex_structure():
    """Demonstrate Plex client response structure"""
    print("=" * 60)
    print("Plex API Response Structure")
    print("=" * 60)
    print()

    print("Sample audiobook data from Plex API:")
    print()

    audiobook_sample = {
        "id": "plex_artist_456",
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "narrator": "Rob Inglis",
        "cover_url": "http://plex-server:32400/library/metadata/456/thumb",
        "duration": 11 * 3600,  # 11 hours in seconds
        "chapters": [
            {
                "id": "plex_track_1",
                "title": "Chapter 1: An Unexpected Party",
                "index": 0,
                "duration": 900.0,
                "audio_file": "http://plex-server:32400/library/parts/789/file.mp3"
            },
            {
                "id": "plex_track_2",
                "title": "Chapter 2: Roast Mutton",
                "index": 1,
                "duration": 850.0,
                "audio_file": "http://plex-server:32400/library/parts/790/file.mp3"
            }
        ]
    }

    print(f"Title: {audiobook_sample['title']}")
    print(f"Author: {audiobook_sample['author']}")
    print(f"Narrator: {audiobook_sample['narrator']}")
    print(f"Chapters: {len(audiobook_sample['chapters'])}")
    print(f"Duration: {audiobook_sample['duration'] / 3600:.1f} hours")
    print()


def demo_database_integration():
    """Demonstrate database storage of audiobooks from servers"""
    print("=" * 60)
    print("Database Integration Demo")
    print("=" * 60)
    print()

    # Initialize database
    print("[1] Initializing database...")
    db = init_database()
    print(f"    [OK] Database: {db.db_path}")
    print()

    # Create servers
    print("[2] Creating server entries...")
    session = get_session()
    server_repo = ServerRepository(session)

    # Audiobookshelf server
    abs_server = server_repo.create(
        server_id="abs_demo",
        type="audiobookshelf",
        name="Demo Audiobookshelf",
        url="http://192.168.1.100:80",
        username="demo",
        password="demo"
    )
    abs_server_id = abs_server.id
    abs_server_name = abs_server.name
    print(f"    [OK] Created Audiobookshelf server: {abs_server_name}")

    # Plex server
    plex_server = server_repo.create(
        server_id="plex_demo",
        type="plex",
        name="Demo Plex Server",
        url="http://192.168.1.100:32400",
        api_key="demo_token_123"
    )
    plex_server_name = plex_server.name
    print(f"    [OK] Created Plex server: {plex_server_name}")
    session.close()
    print()

    # Add audiobooks
    print("[3] Adding audiobooks from Audiobookshelf...")
    session = get_session()
    book_repo = BookRepository(session)

    audiobook_data = {
        "id": "abs_gatsby",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "narrator": "Jake Gyllenhaal",
        "duration": 9.5 * 3600,
        "chapters": [
            {
                "id": "ch_1",
                "title": "Chapter 1",
                "index": 0,
                "duration": 1200.0,
                "audio_file": "http://abs-server/api/books/gatsby/stream"
            }
        ]
    }

    book = book_repo.create(
        book_id=audiobook_data["id"],
        server_id=abs_server_id,
        library_id="abs_library_1",
        title=audiobook_data["title"],
        author=audiobook_data["author"],
        narrator=audiobook_data["narrator"],
        duration=audiobook_data["duration"],
        chapters=audiobook_data["chapters"]
    )
    print(f"    [OK] Added audiobook: {book.title}")
    print(f"         From server: {abs_server_name}")
    print(f"         Chapters: {len(book.chapters)}")
    print(f"         Duration: {book.duration / 3600:.1f} hours")
    session.close()
    print()

    # Query audiobooks
    print("[4] Querying audiobooks from database...")
    session = get_session()
    books = session.query(Book).all()
    print(f"    [OK] Total audiobooks in database: {len(books)}")
    for book in books:
        server = book.server
        print(f"        - {book.title} ({server.name})")
    session.close()
    print()


def show_api_structure():
    """Show the API client structure and usage"""
    print("=" * 60)
    print("API Client Architecture")
    print("=" * 60)
    print()

    print("File Structure:")
    print("  app/clients/")
    print("    - plex_client.py:      Plex API integration")
    print("    - audiobookshelf_client.py: Audiobookshelf API integration")
    print("    - __init__.py:         Module exports")
    print()

    print("File Structure:")
    print("  app/sync/")
    print("    - scanner.py:          Server scanner and sync orchestrator")
    print("    - __init__.py:         Module exports")
    print()

    print("Key Classes:")
    print("  - PlexClient: Handles Plex server connections and audiobook discovery")
    print("  - AudiobookshelfClient: Handles Audiobookshelf connections")
    print("  - ServerScanner: Orchestrates scanning and database sync")
    print()

    print("Usage Flow:")
    print("  1. PlexClient/AudiobookshelfClient discover audiobooks on server")
    print("  2. ServerScanner fetches data from clients")
    print("  3. Scanner stores audiobooks in database")
    print("  4. UI queries database for audiobooks and libraries")
    print("  5. Player uses streaming URLs from database")
    print()


if __name__ == "__main__":
    print()
    print("Audook API Client Architecture Demo")
    print()

    # Show architecture
    show_api_structure()

    # Show data structures
    demo_audiobookshelf_structure()
    print()
    demo_plex_structure()
    print()

    # Show database integration
    demo_database_integration()

    print("=" * 60)
    print("Demo Complete")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("  1. Configure your Plex/Audiobookshelf servers in the database")
    print("  2. Run scanner.scan_all_servers() to discover audiobooks")
    print("  3. UI will display discovered audiobooks from servers")
    print()
