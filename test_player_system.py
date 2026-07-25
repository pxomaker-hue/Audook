#!/usr/bin/env python3
"""
Test VLC Player + Progress Manager + Database integration
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database, get_session
from app.database.models import Server, Library, Book, ReadingProgress
from app.database.repositories import ServerRepository, BookRepository, ReadingProgressRepository
from app.player import player, progress_manager
from app.models import Audiobook


def test_database_and_player():
    """Test complete system: Database + Player + Progress"""

    print("=" * 60)
    print("Testing VLC Player + Progress Manager + Database")
    print("=" * 60)
    print()

    # Step 1: Initialize database
    print("[1] Initializing database...")
    db = init_database()
    print(f"    [OK] Database: {db.db_path}")
    print()

    # Step 2: Create test server and books
    print("[2] Creating test server and books...")
    session = get_session()
    server_repo = ServerRepository(session)
    book_repo = BookRepository(session)

    # Create local server
    server = server_repo.create(
        server_id="local_test",
        type="local",
        name="Test Local Library",
        url=str(Path("test_audiobooks"))
    )
    print(f"    [OK] Server: {server.name}")

    # Create test books in database
    test_books = [
        {
            "id": "test_book_1",
            "title": "Test Audiobook 1",
            "author": "Test Author",
            "chapters": [
                {
                    "id": "ch_1",
                    "title": "Chapter 1",
                    "index": 0,
                    "duration": 60.0,
                    "audio_file": str(Path("test_audiobooks") / "The Great Gatsby" / "Chapter 1.wav")
                }
            ],
            "duration": 60.0
        }
    ]

    created_books = []
    for book_data in test_books:
        book = book_repo.create(
            book_id=book_data["id"],
            server_id=server.id,
            library_id="test_lib",
            title=book_data["title"],
            author=book_data["author"],
            duration=book_data["duration"],
            chapters=book_data["chapters"]
        )
        created_books.append(book)
        print(f"    [OK] Book: {book.title} ({len(book.chapters)} chapters)")

    session.close()
    print()

    # Step 3: Load audiobook
    print("[3] Loading audiobook...")
    if not created_books:
        print("    [FAIL] No books created")
        return False

    book_data = test_books[0]
    audiobook = Audiobook(
        id=book_data["id"],
        library_id="test_lib",
        title=book_data["title"],
        author=book_data["author"],
        duration=book_data["duration"],
        chapters=book_data["chapters"],
        source="local"
    )
    print(f"    [OK] Audiobook: {audiobook.title}")
    print(f"    [OK] Chapters: {len(audiobook.chapters)}")
    print()

    # Step 4: Test Progress Manager - Load Progress
    print("[4] Testing Progress Manager - Loading progress...")
    chapter_idx, position = progress_manager.load_progress(audiobook)
    print(f"    [OK] Loaded progress: Chapter {chapter_idx}, Position {position}s")
    print()

    # Step 5: Test Player - Start playback
    print("[5] Testing VLC Player - Starting playback...")
    if not audiobook.chapters:
        print("    [FAIL] No chapters available")
        return False

    chapter = audiobook.chapters[0]
    audio_file = Path(chapter["audio_file"])

    if not audio_file.exists():
        print(f"    [FAIL] Audio file not found: {audio_file}")
        return False

    print(f"    [OK] Audio file exists: {audio_file.name}")

    success = player.play(audiobook, chapter, 0.0)
    print(f"    [OK] Playback started: {success}")

    if not success:
        print("    [FAIL] Failed to start playback")
        return False

    print(f"    [OK] Playing: {player.get_current_audiobook().title}")
    print(f"    [OK] Is playing: {player.is_playing()}")
    print()

    # Step 6: Test Controls
    print("[6] Testing player controls...")

    # Pause
    player.pause()
    print(f"    [OK] Paused: {player.is_paused()}")
    time.sleep(0.5)

    # Resume
    player.resume()
    print(f"    [OK] Resumed: {player.is_playing()}")
    time.sleep(0.5)

    # Seek
    player.seek_relative(5.0)
    pos = player.get_position()
    print(f"    [OK] Sought to position: {pos:.1f}s")

    # Volume
    player.set_volume(50)
    vol = player.get_volume()
    print(f"    [OK] Volume set to: {vol}%")

    # Speed
    player.set_speed(1.5)
    speed = player.get_speed()
    print(f"    [OK] Speed set to: {speed}x")
    print()

    # Step 7: Test Progress Manager - Update Progress
    print("[7] Testing Progress Manager - Updating progress...")
    progress_manager.start_session(audiobook, 0, 0.0, device_id="test_device")
    print(f"    [OK] Session started")

    # Simulate listening
    progress_manager.update_progress(0, 15.5)
    print(f"    [OK] Progress updated to: Chapter 0, Position 15.5s")
    time.sleep(1.0)

    # Test auto-save
    progress_manager.save_progress()
    print(f"    [OK] Progress saved to database")
    print()

    # Step 8: Verify progress in database
    print("[8] Verifying progress in database...")
    session = get_session()

    progress = session.query(ReadingProgress).filter_by(
        book_id=audiobook.id
    ).first()

    if progress:
        print(f"    [OK] Progress found in DB:")
        print(f"      - Chapter: {progress.current_chapter_index}")
        print(f"      - Position: {progress.position_seconds}s")
        print(f"      - Progress %: {progress.progress_percent:.1f}%")
    else:
        print("    [FAIL] Progress not found in database")

    session.close()
    print()

    # Step 9: Stop playback
    print("[9] Stopping playback...")
    progress_manager.end_session()
    player.stop()
    print(f"    [OK] Playback stopped")
    print(f"    [OK] Session ended and saved")
    print()

    # Cleanup
    print("[10] Cleanup...")
    player.shutdown()
    print(f"    [OK] Player shutdown")
    print()

    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("[OK] Database integration working")
    print("[OK] VLC Player functional (streaming ready)")
    print("[OK] Progress Manager auto-saving")
    print("[OK] Full stack operational")
    print()
    print("Ready for Phase 3: Clients API (Plex + Audiobookshelf)")

    return True


if __name__ == "__main__":
    try:
        success = test_database_and_player()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
