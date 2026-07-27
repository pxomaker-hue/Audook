"""
Local audiobook folder scanner
Recursively scan folders for audiobook files
"""

import re
from pathlib import Path
from typing import List, Optional

import mutagen

from app import CACHE_DIR
from app.models import Audiobook, Library
from app.utils import logger

# Supported audio formats
AUDIO_EXTENSIONS = {'.mp3', '.m4b', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}


def _clean_tag(value: Optional[str]) -> Optional[str]:
    """Ripping tools frequently write tag values as filename-safe strings
    with underscores instead of spaces (e.g. "J_K_Rowling",
    "Isaac_Asimov") - turn those back into normal display text."""
    if not value:
        return value
    return re.sub(r'_+', ' ', value).strip() or None


def _primary_name(value: Optional[str]) -> Optional[str]:
    """First name only, dropping a comma-separated translator/narrator
    credit some publishers stuff into the same tag (e.g. "Andrzej
    Sapkowski, Lydia Cantin-Waleryszak - traducteur")."""
    if not value:
        return value
    return value.split(',')[0].strip() or None


def _is_usable_albumartist(albumartist: Optional[str], artist: Optional[str]) -> bool:
    """Some publishers (e.g. Audiolib) write a malformed albumartist tag -
    a duplicate of the artist tag with a dangling "Lu par :" ("Narrated
    by:") label and stray tab characters appended, meant to be followed by
    a narrator name that never made it in. That's worse than the artist
    tag, not a cleaner author source, so it must be rejected rather than
    trusted just because it differs from artist."""
    if not albumartist or albumartist == artist:
        return False
    if '\t' in albumartist or '\n' in albumartist:
        return False
    if 'lu par' in albumartist.lower():
        return False
    return True

# Common sibling cover-image filenames, checked in order
COVER_FILENAMES = ['cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.jpeg', 'folder.png']

# Base URL of this same backend, used to build local-cover URLs the
# frontend can load like any other cover_url - see GET /api/local-cover/<id>
# in audook_backend.py.
BACKEND_BASE_URL = "http://127.0.0.1:5000"


class LocalAudiobookScanner:
    """Scanner for local audiobook folders.

    Handles both common layouts transparently:
      - Flat:   <root>/<Book>/*.mp3
      - Nested: <root>/<Author>/<Book>/*.mp3
    A directory is treated as "a book" the moment it directly contains audio
    files - whichever level that happens at. This is what a plain one-level
    scan used to miss entirely: a folder like <root>/Dune/ that holds seven
    book subfolders but no audio files of its own used to be skipped outright
    (no audio files at that level), silently dropping every book under it.
    """

    def __init__(self):
        self.logger = logger

    async def scan_folder(self, folder_path: Path) -> List[Audiobook]:
        """Scan a folder (at any depth) for audiobook folders."""
        audiobooks = []

        if not folder_path.exists():
            self.logger.error(f"Folder not found: {folder_path}")
            return audiobooks

        for book_dir in self._find_book_dirs(folder_path):
            audiobook = self._scan_audiobook_folder(book_dir, folder_path)
            if audiobook:
                audiobooks.append(audiobook)

        return audiobooks

    def _find_book_dirs(self, root: Path) -> List[Path]:
        """Depth-first search for every directory that directly contains
        audio files. Doesn't recurse further into a directory once it's
        been identified as a book (its own subfolders, if any, are assumed
        to be part of that book, not separate books)."""
        book_dirs: List[Path] = []

        def walk(directory: Path):
            try:
                entries = list(directory.iterdir())
            except Exception as e:
                self.logger.warning(f"Failed to read directory {directory}: {e}")
                return

            has_audio = any(e.is_file() and e.suffix.lower() in AUDIO_EXTENSIONS for e in entries)
            if has_audio:
                book_dirs.append(directory)
                return

            for entry in entries:
                if entry.is_dir():
                    walk(entry)

        walk(root)
        return book_dirs

    def _scan_audiobook_folder(self, audiobook_folder: Path, root: Path) -> Optional[Audiobook]:
        """Scan a single audiobook folder (one that directly contains audio
        files) into an Audiobook, reading real tags/duration/cover art
        instead of guessing from the folder name."""
        audio_files = []
        for ext in AUDIO_EXTENSIONS:
            audio_files.extend(sorted(audiobook_folder.glob(f'*{ext}')))

        if not audio_files:
            return None

        first_tags = self._read_tags(audio_files[0])

        # Title: prefer the shared album tag, fall back to the folder name.
        title = _clean_tag(first_tags.get('album')) or audiobook_folder.name

        # Author: French audiobook rips very commonly tag the NARRATOR as
        # 'artist' (the voice actor, e.g. "Dominique_Collignon-Maurin") and
        # put the real author under 'albumartist' (e.g. "J_K_Rowling") -
        # ID3/MP4 have no dedicated "book author" field so ripping tools
        # overload whichever tag is convenient, and the convention isn't
        # even consistent within the same library: some publishers (e.g.
        # Audiolib) instead leave a usable author in 'artist' (occasionally
        # with a translator credit tacked on after a comma) and put the
        # narrator under 'composer', with 'albumartist' left malformed/
        # unusable. Try the cleanest signal first, in order.
        artist = _clean_tag(first_tags.get('artist'))
        albumartist = _clean_tag(first_tags.get('albumartist'))
        composer = _clean_tag(first_tags.get('composer'))
        if _is_usable_albumartist(albumartist, artist):
            author = albumartist
            narrator = artist
        else:
            author = _primary_name(artist) or albumartist
            narrator = composer
        if not author:
            parent = audiobook_folder.parent
            author = parent.name if parent != root else "Auteur inconnu"

        audiobook_id = f"local_{audiobook_folder.name}".replace(" ", "_")

        chapters = []
        total_duration = 0.0
        for idx, audio_file in enumerate(audio_files):
            tags = first_tags if audio_file == audio_files[0] else self._read_tags(audio_file)
            duration = tags.get('duration') or 0.0
            total_duration += duration
            chapters.append({
                "id": f"ch_{idx}",
                "title": _clean_tag(tags.get('title')) or _clean_tag(audio_file.stem),
                "index": idx,
                "duration": duration,
                "start": 0.0,
                "audio_file": str(audio_file),
            })

        cover_url = self._resolve_cover(audiobook_folder, audio_files[0], audiobook_id)

        return Audiobook(
            id=audiobook_id,
            library_id="local",
            title=title,
            author=author,
            narrator=narrator,
            description=f"{len(chapters)} chapitres",
            cover=cover_url,
            duration=total_duration,
            chapters=chapters,
            source="local",
            local_path=audiobook_folder,
            is_downloaded=True,
        )

    def _read_tags(self, audio_file: Path) -> dict:
        """Read title/artist/album tags and real duration via mutagen.
        Returns an empty dict (never raises) if the file can't be parsed -
        callers already fall back to the filename/folder name in that
        case."""
        try:
            audio = mutagen.File(str(audio_file), easy=True)
            if audio is None:
                return {}
            tags = audio.tags or {}
            return {
                'title': (tags.get('title') or [None])[0],
                'artist': (tags.get('artist') or [None])[0],
                'albumartist': (tags.get('albumartist') or [None])[0],
                'composer': (tags.get('composer') or [None])[0],
                'album': (tags.get('album') or [None])[0],
                'duration': audio.info.length if getattr(audio, 'info', None) else None,
            }
        except Exception as e:
            self.logger.warning(f"Failed to read tags for {audio_file}: {e}")
            return {}

    def _find_sibling_cover(self, folder: Path) -> Optional[Path]:
        """A cover/folder image file sitting next to the audio files -
        extremely common in audiobook rips and the simplest, most reliable
        source when present."""
        for name in COVER_FILENAMES:
            candidate = folder / name
            if candidate.exists():
                return candidate
        return None

    def _extract_embedded_cover(self, audio_file: Path) -> Optional[bytes]:
        """Embedded cover art (ID3 APIC for mp3, MP4 'covr' atom for m4b/m4a,
        FLAC picture blocks) - used when there's no sibling cover file."""
        try:
            audio = mutagen.File(str(audio_file))
            if audio is None:
                return None

            # FLAC/OGG-style: a `.pictures` list of Picture objects
            pictures = getattr(audio, 'pictures', None)
            if pictures:
                return pictures[0].data

            # MP4/M4A/M4B: 'covr' atom, a list of MP4Cover (bytes-like)
            if 'covr' in audio:
                covers = audio['covr']
                if covers:
                    return bytes(covers[0])

            # ID3 (mp3): APIC frames
            tags = getattr(audio, 'tags', None)
            if tags:
                for key in tags.keys():
                    if str(key).startswith('APIC'):
                        return tags[key].data
        except Exception as e:
            self.logger.warning(f"Failed to extract embedded cover from {audio_file}: {e}")

        return None

    def _resolve_cover(self, folder: Path, first_audio_file: Path, book_id: str) -> Optional[str]:
        """Cache a cover image (sibling file preferred, embedded tag as
        fallback) and return the URL to serve it from - or None if neither
        source has one, same as before."""
        cover_bytes = None
        ext = 'jpg'

        sibling = self._find_sibling_cover(folder)
        if sibling:
            try:
                cover_bytes = sibling.read_bytes()
                ext = sibling.suffix.lstrip('.').lower() or 'jpg'
            except Exception as e:
                self.logger.warning(f"Failed to read sibling cover {sibling}: {e}")

        if cover_bytes is None:
            cover_bytes = self._extract_embedded_cover(first_audio_file)

        if not cover_bytes:
            return None

        try:
            cache_path = CACHE_DIR / f"local_cover_{book_id}.{ext}"
            cache_path.write_bytes(cover_bytes)
            return f"{BACKEND_BASE_URL}/api/local-cover/{book_id}"
        except Exception as e:
            self.logger.warning(f"Failed to cache local cover for {book_id}: {e}")
            return None


def get_local_library(folder_path: Path) -> Library:
    """Create a Library object for a local folder"""
    return Library(
        id="local",
        name=f"Local: {folder_path.name}",
        source="local",
        server_url=str(folder_path),
    )
