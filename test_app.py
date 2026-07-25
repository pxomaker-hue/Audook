#!/usr/bin/env python3
"""
Test script for Audook
Run this to verify the application works correctly
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
 """Test that all imports work"""
 print("Testing imports...")
 
 try:
 from app import __version__, APP_NAME, DATA_DIR, CONFIG_FILE
 print(f"✓ App module: v{__version__}")
 
 from app.models import Audiobook, Chapter, Library, Bookmark, PlaybackState, ServerConfig, AppConfig
 print("✓ Models")
 
 from app.utils import format_duration, format_time_short, generate_id, sanitize_filename
 print("✓ Utilities")
 
 from app.utils.config_manager import config_manager
 print("✓ Config Manager")
 
 from app.audiobookshelf.client import AudiobookshelfClient
 print("✓ Audiobookshelf Client")
 
 from app.plex.client import PlexClient
 print("✓ Plex Client")
 
 from app.player.player import player
 from app.player.queue import queue
 print("✓ Player")
 
 from app.ui import get_stylesheet, apply_theme
 print("✓ UI Utilities")
 
 from app.ui.library_view import LibraryView
 from app.ui.player_view import PlayerView
 from app.ui.settings_view import SettingsView
 print("✓ UI Components")
 
 from app.main_window import MainWindow
 print("✓ Main Window")
 
 print("\n✅ All imports successful!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Import failed: {e}")
 import traceback
 traceback.print_exc()
 return False


def test_models():
 """Test data models"""
 print("Testing models...")
 
 try:
 from app.models import Audiobook, Chapter, Library, Bookmark, PlaybackState, ServerConfig
 from datetime import datetime
 
 # Test Audiobook
 audiobook = Audiobook(
 id="test123",
 library_id="lib123",
 title="Test Audiobook",
 author="Test Author",
 narrator="Test Narrator",
 description="Test description",
 duration=3600.0,
 source="audiobookshelf"
 )
 assert audiobook.display_title == "Test Audiobook - Test Author"
 print("✓ Audiobook model")
 
 # Test Chapter
 chapter = Chapter(
 id="chap1",
 title="Chapter 1",
 index=0,
 duration=1800.0,
 audio_file="/path/to/audio.mp3"
 )
 assert chapter.display_title == "1. Chapter 1"
 print("✓ Chapter model")
 
 # Test Library
 library = Library(
 id="lib123",
 name="Test Library",
 source="audiobookshelf",
 server_url="http://localhost:13378"
 )
 print("✓ Library model")
 
 # Test Bookmark
 bookmark = Bookmark(
 book_id="test123",
 library_id="lib123",
 chapter_id="chap1",
 position=600.0,
 title="My Bookmark"
 )
 print("✓ Bookmark model")
 
 # Test PlaybackState
 state = PlaybackState(
 book_id="test123",
 library_id="lib123",
 chapter_id="chap1",
 position=600.0,
 is_playing=True,
 speed=1.0
 )
 print("✓ PlaybackState model")
 
 # Test ServerConfig
 server = ServerConfig(
 id="server1",
 name="My Server",
 type="audiobookshelf",
 url="http://localhost:13378",
 api_key="test-key"
 )
 print("✓ ServerConfig model")
 
 print("\n✅ All model tests passed!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Model test failed: {e}")
 import traceback
 traceback.print_exc()
 return False


def test_utils():
 """Test utility functions"""
 print("Testing utilities...")
 
 try:
 from app.utils import format_duration, format_time_short, generate_id, sanitize_filename
 
 # Test format_duration
 assert format_duration(0) == "00:00"
 assert format_duration(60) == "01:00"
 assert format_duration(3661) == "01:01:01"
 print("✓ format_duration")
 
 # Test format_time_short
 assert format_time_short(60) == "1m 0s"
 assert format_time_short(3661) == "1h 1m"
 print("✓ format_time_short")
 
 # Test generate_id
 id1 = generate_id("test_")
 id2 = generate_id("test_")
 assert id1 != id2
 assert id1.startswith("test_")
 print("✓ generate_id")
 
 # Test sanitize_filename
 assert sanitize_filename("Test: File*Name?.txt") == "Test_File_Name.txt"
 print("✓ sanitize_filename")
 
 print("\n✅ All utility tests passed!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Utility test failed: {e}")
 import traceback
 traceback.print_exc()
 return False


def test_config():
 """Test configuration"""
 print("Testing configuration...")
 
 try:
 from app.utils.config_manager import config_manager
 from app.models import ServerConfig
 
 # Test config loading
 config = config_manager.config
 assert hasattr(config, 'servers')
 assert hasattr(config, 'theme')
 print("✓ Config loading")
 
 # Test server management
 test_server = ServerConfig(
 id="test_server",
 name="Test Server",
 type="audiobookshelf",
 url="http://localhost:13378",
 api_key="test-key"
 )
 
 # Add server
 config_manager.add_server(test_server)
 assert len(config_manager.config.servers) > 0
 print("✓ Add server")
 
 # Remove server
 config_manager.remove_server("test_server")
 print("✓ Remove server")
 
 print("\n✅ All config tests passed!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Config test failed: {e}")
 import traceback
 traceback.print_exc()
 return False


async def test_clients():
 """Test API clients (without actual connections)"""
 print("Testing API clients...")
 
 try:
 from app.audiobookshelf.client import AudiobookshelfClient
 from app.plex.client import PlexClient
 
 # Test AudiobookshelfClient instantiation
 abs_client = AudiobookshelfClient("http://localhost:13378", "test-key")
 assert abs_client.base_url == "http://localhost:13378"
 assert abs_client.api_key == "test-key"
 abs_client.close()
 print("✓ AudiobookshelfClient")
 
 # Test PlexClient instantiation
 plex_client = PlexClient("http://localhost:32400", "test-token")
 assert plex_client.base_url == "http://localhost:32400"
 assert plex_client.token == "test-token"
 plex_client.close()
 print("✓ PlexClient")
 
 print("\n✅ All client tests passed!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Client test failed: {e}")
 import traceback
 traceback.print_exc()
 return False


def test_player():
 """Test player (without actual audio)"""
 print("Testing player...")
 
 try:
 from app.player.player import player
 from app.player.queue import queue
 
 # Test player state
 assert player.get_volume() == 0.8 # Default
 assert player.get_speed() == 1.0 # Default
 assert not player.is_playing()
 print("✓ Player state")
 
 # Test queue
 assert queue.is_empty()
 print("✓ Queue")
 
 print("\n✅ All player tests passed!\n")
 return True
 
 except Exception as e:
 print(f"\n❌ Player test failed: {e}")
 import traceback
 traceback.print_exc()
 return False


def main():
 """Run all tests"""
 print("=" * 60)
 print("Audook - Test Suite")
 print("=" * 60)
 print()
 
 results = []
 
 # Run synchronous tests
 results.append(("Imports", test_imports()))
 results.append(("Models", test_models()))
 results.append(("Utilities", test_utils()))
 results.append(("Config", test_config()))
 results.append(("Player", test_player()))
 
 # Run async tests
 results.append(("Clients", asyncio.run(test_clients())))
 
 # Summary
 print("=" * 60)
 print("Test Summary")
 print("=" * 60)
 
 passed = sum(1 for _, result in results if result)
 total = len(results)
 
 for name, result in results:
 status = "✅ PASS" if result else "❌ FAIL"
 print(f"{name:20s} {status}")
 
 print()
 print(f"Results: {passed}/{total} tests passed")
 
 if passed == total:
 print("\n🎉 All tests passed! The application is ready to use.")
 return 0
 else:
 print("\n⚠️ Some tests failed. Please check the output above.")
 return 1


if __name__ == "__main__":
 sys.exit(main())
