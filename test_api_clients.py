#!/usr/bin/env python3
"""
Test API clients for Plex and Audiobookshelf
Demonstrates server connection and audiobook discovery
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database, get_session, ServerRepository
from app.clients import AudiobookshelfClient
from app.sync import scanner


def test_audiobookshelf_client():
    """Test Audiobookshelf client"""
    print("=" * 60)
    print("Testing Audiobookshelf API Client")
    print("=" * 60)
    print()

    # Note: These are test credentials - replace with your actual server
    # For testing, we'll use a mock server config
    abs_url = "http://192.168.1.100:80"  # Replace with your ABS server IP
    abs_username = "admin"  # Replace with your username
    abs_password = "password"  # Replace with your password

    print("[1] Testing Audiobookshelf connection...")
    print(f"    URL: {abs_url}")

    try:
        client = AudiobookshelfClient(abs_url, abs_username, abs_password)

        if client.test_connection():
            print("    [OK] Connected to Audiobookshelf")
        else:
            print("    [FAIL] Connection test failed")
            return False

        # Get libraries
        print()
        print("[2] Fetching libraries...")
        libraries = client.get_libraries()

        if libraries:
            print(f"    [OK] Found {len(libraries)} libraries:")
            for lib in libraries:
                print(f"        - {lib['name']} (ID: {lib['id']})")
        else:
            print("    [FAIL] No libraries found or authentication failed")
            return False

        # Get audiobooks from first library
        if libraries:
            lib_id = libraries[0]["id"]
            print()
            print(f"[3] Fetching audiobooks from '{libraries[0]['name']}'...")

            audiobooks = client.get_audiobooks(lib_id)

            if audiobooks:
                print(f"    [OK] Found {len(audiobooks)} audiobooks:")
                for book in audiobooks[:3]:  # Show first 3
                    print(f"        - {book['title']}")
                    print(f"          Author: {book.get('author')}")
                    print(f"          Chapters: {len(book.get('chapters', []))}")
                    print(f"          Duration: {book['duration']:.1f}s")
            else:
                print("    [FAIL] No audiobooks found")

        return True

    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def test_scanner_integration():
    """Test scanner with database integration"""
    print()
    print("=" * 60)
    print("Testing Scanner Integration")
    print("=" * 60)
    print()

    # Initialize database
    print("[1] Initializing database...")
    db = init_database()
    print(f"    [OK] Database: {db.db_path}")
    print()

    # Create server config in database
    print("[2] Adding Audiobookshelf server to database...")
    session = get_session()
    server_repo = ServerRepository(session)

    server = server_repo.create(
        server_id="test_abs_server",
        type="audiobookshelf",
        name="Test Audiobookshelf",
        url="http://192.168.1.100:80",
        username="admin",
        password="password"
    )
    print(f"    [OK] Server created: {server.name}")
    session.close()
    print()

    # Test scanner
    print("[3] Testing scanner on configured server...")
    try:
        session = get_session()
        test_server = session.query(ServerRepository.__class__.__bases__[0]).filter_by(
            id="test_abs_server"
        ).first()

        if test_server:
            result = scanner.scan_server(test_server)
            if result:
                print("    [OK] Scan completed successfully")
            else:
                print("    [FAIL] Scan failed (server unreachable or auth failed)")
        else:
            print("    [FAIL] Server not found in database")

        session.close()

    except Exception as e:
        print(f"    [ERROR] {e}")
        return False

    print()
    print("Scanner integration test complete")
    return True


def show_usage():
    """Show usage instructions"""
    print()
    print("=" * 60)
    print("API Client Usage Instructions")
    print("=" * 60)
    print()
    print("Before running full tests, configure your servers:")
    print()
    print("1. Audiobookshelf:")
    print("   - Update the abs_url, abs_username, abs_password in test_audiobookshelf_client()")
    print()
    print("2. Plex:")
    print("   - Similar setup required for PlexClient")
    print("   - Requires python-plexapi library")
    print()
    print("Configuration values needed:")
    print("  - Server URL (e.g., http://192.168.1.100:80)")
    print("  - Authentication credentials (username/password or token)")
    print()


if __name__ == "__main__":
    print()
    print("Audook API Client Tests")
    print()

    # Show usage first
    show_usage()

    print()
    print("To test with your actual servers:")
    print("1. Edit this script and update server credentials")
    print("2. Run: python test_api_clients.py")
    print()
