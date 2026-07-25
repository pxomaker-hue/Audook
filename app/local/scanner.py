"""
Local audiobook folder scanner
Recursively scan folders for audiobook files
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from app.models import Audiobook, Library
from app.utils import logger, format_duration

# Supported audio formats
AUDIO_EXTENSIONS = {'.mp3', '.m4b', '.flac', '.ogg', '.wav', '.aac', '.opus'}


class LocalAudiobookScanner:
    """Scanner for local audiobook folders"""

    def __init__(self):
        self.logger = logger

    async def scan_folder(self, folder_path: Path) -> List[Audiobook]:
        """
        Scan a folder for audiobook files
        Expects structure: folder/audiobook_name/chapter_files.mp3
        """
        audiobooks = []

        if not folder_path.exists():
            self.logger.error(f"Folder not found: {folder_path}")
            return audiobooks

        # Scan for subdirectories (each is an audiobook)
        for item in folder_path.iterdir():
            if not item.is_dir():
                continue

            audiobook = await self._scan_audiobook_folder(item)
            if audiobook:
                audiobooks.append(audiobook)

        return audiobooks

    async def _scan_audiobook_folder(self, audiobook_folder: Path) -> Optional[Audiobook]:
        """Scan a single audiobook folder"""
        # Find all audio files
        audio_files = []
        for ext in AUDIO_EXTENSIONS:
            audio_files.extend(sorted(audiobook_folder.glob(f'*{ext}')))

        if not audio_files:
            return None

        # Create audiobook from folder
        audiobook_title = audiobook_folder.name
        audiobook_id = f"local_{audiobook_folder.name}".replace(" ", "_")

        # Build chapters from audio files
        chapters = []
        total_duration = 0.0

        for idx, audio_file in enumerate(audio_files):
            duration = self._get_file_duration(audio_file)
            total_duration += duration

            chapter = {
                "id": f"ch_{idx}",
                "title": audio_file.stem,
                "index": idx,
                "duration": duration,
                "start": 0.0,
                "audio_file": str(audio_file),
            }
            chapters.append(chapter)

        audiobook = Audiobook(
            id=audiobook_id,
            library_id="local",
            title=audiobook_title,
            author="Audiobook local",
            narrator=None,
            description=f"{len(chapters)} chapitres",
            cover=None,
            duration=total_duration,
            chapters=chapters,
            source="local",
            local_path=audiobook_folder,
            is_downloaded=True,
        )

        return audiobook

    def _get_file_duration(self, audio_file: Path) -> float:
        """
        Get duration of audio file in seconds
        Uses a simple estimation based on file size
        TODO: Use proper audio library to get actual duration
        """
        try:
            # For now, return a placeholder duration
            # In production, use mutagen or librosa to get actual duration
            return 3600.0  # 1 hour placeholder
        except Exception as e:
            self.logger.error(f"Error getting duration for {audio_file}: {e}")
            return 0.0


def get_local_library(folder_path: Path) -> Library:
    """Create a Library object for a local folder"""
    return Library(
        id="local",
        name=f"Local: {folder_path.name}",
        source="local",
        server_url=str(folder_path),
    )
