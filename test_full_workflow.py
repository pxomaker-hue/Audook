#!/usr/bin/env python3
"""
Test the complete workflow - Simulate user interaction
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.local.client import LocalClient
from app.player.player import player
from app.utils import logger


async def test_complete_workflow():
    """Test complete workflow"""
    print("=" * 60)
    print("Testing Complete Audook Workflow")
    print("=" * 60)
    print()

    # Step 1: Initialize local client
    print("[1] Initializing local client...")
    test_folder = Path("test_audiobooks")
    client = LocalClient(str(test_folder))

    is_accessible = await client.ping()
    print(f"    Folder accessible: {is_accessible}")
    if not is_accessible:
        print("    ERROR: Folder not accessible!")
        return False

    # Step 2: Get libraries
    print("\n[2] Loading libraries...")
    libraries = await client.get_libraries()
    print(f"    Found {len(libraries)} library/libraries")
    for lib in libraries:
        print(f"    - {lib.name}")

    if not libraries:
        print("    ERROR: No libraries found!")
        return False

    # Step 3: Get audiobooks
    print("\n[3] Loading audiobooks...")
    library = libraries[0]
    audiobooks = await client.get_audiobooks(library.id, limit=100)
    print(f"    Found {len(audiobooks)} audiobook(s)")
    for ab in audiobooks[:3]:  # Show first 3
        print(f"    - {ab.title} ({len(ab.chapters)} chapters)")

    if not audiobooks:
        print("    ERROR: No audiobooks found!")
        return False

    # Step 4: Select and play first audiobook
    print("\n[4] Testing playback...")
    audiobook = audiobooks[0]
    chapter = audiobook.chapters[0] if audiobook.chapters else None

    if not chapter:
        print("    ERROR: No chapters found!")
        return False

    print(f"    Playing: {audiobook.title}")
    print(f"    Chapter: {chapter.get('title')}")
    print(f"    File: {chapter.get('audio_file')}")

    # Check if file exists
    audio_file = Path(chapter.get('audio_file', ''))
    if not audio_file.exists():
        print(f"    ERROR: Audio file not found: {audio_file}")
        return False

    print(f"    Audio file exists: YES")

    # Step 5: Try to start playback
    print("\n[5] Starting playback...")
    success = player.play(audiobook, chapter)
    print(f"    Playback started: {success}")

    if not success:
        print("    ERROR: Could not start playback!")
        return False

    # Step 6: Test controls
    print("\n[6] Testing player controls...")

    # Check state
    is_playing = player.is_playing()
    print(f"    Is playing: {is_playing}")

    position = player.get_current_position()
    print(f"    Position: {position:.1f}s")

    volume = player.get_volume()
    print(f"    Volume: {volume * 100:.0f}%")

    speed = player.get_speed()
    print(f"    Speed: {speed}x")

    # Test pause
    print("\n[7] Testing pause...")
    player.pause()
    is_playing = player.is_playing()
    print(f"    Is playing after pause: {is_playing}")

    # Test resume
    print("\n[8] Testing resume...")
    player.resume()
    is_playing = player.is_playing()
    print(f"    Is playing after resume: {is_playing}")

    # Test seek
    print("\n[9] Testing seek...")
    player.seek_relative(10)
    position = player.get_current_position()
    print(f"    Position after seek +10s: {position:.1f}s")

    # Test volume
    print("\n[10] Testing volume control...")
    player.set_volume(0.5)
    volume = player.get_volume()
    print(f"    Volume set to: {volume * 100:.0f}%")

    # Cleanup
    print("\n[11] Stopping playback...")
    player.stop()
    is_playing = player.is_playing()
    print(f"    Is playing after stop: {is_playing}")

    client.close()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_complete_workflow())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
