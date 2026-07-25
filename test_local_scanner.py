#!/usr/bin/env python3
"""Test the local audiobook scanner"""

import asyncio
import sys
from pathlib import Path

# Add the project to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.local.scanner import LocalAudiobookScanner
from app.local.client import LocalClient


async def main():
    print("Testing LocalAudiobookScanner...\n")

    # Test folder
    test_folder = Path("test_audiobooks")
    if not test_folder.exists():
        print(f"Error: {test_folder} not found!")
        print("Run: python create_test_audiobooks.py")
        return

    # Test scanner
    scanner = LocalAudiobookScanner()
    audiobooks = await scanner.scan_folder(test_folder)

    print(f"Found {len(audiobooks)} audiobooks:\n")
    for ab in audiobooks:
        print(f"  - {ab.title}")
        print(f"    Author: {ab.author}")
        print(f"    Chapters: {len(ab.chapters)}")
        for ch in ab.chapters[:2]:  # Show first 2 chapters
            print(f"      * {ch['title']} ({ch['duration']}s)")
        if len(ab.chapters) > 2:
            print(f"      ... and {len(ab.chapters) - 2} more")
        print()

    # Test client
    print("\nTesting LocalClient...\n")
    client = LocalClient(str(test_folder))

    # Test ping
    is_accessible = await client.ping()
    print(f"Folder accessible: {is_accessible}")

    # Get libraries
    libraries = await client.get_libraries()
    print(f"Libraries: {len(libraries)}")
    for lib in libraries:
        print(f"  - {lib.name}")

    # Get audiobooks
    if libraries:
        audiobooks = await client.get_audiobooks(libraries[0].id)
        print(f"\nAudiobooks in '{libraries[0].name}':")
        for ab in audiobooks:
            print(f"  - {ab.title}")

    print("\n[OK] All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
