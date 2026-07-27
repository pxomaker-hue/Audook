"""
Utility functions for Audook
"""

import json
import hashlib
import os
import socket
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """Path to the ffmpeg binary to use for loudness measurement/noise
    reduction. Electron sets AUDOOK_FFMPEG_PATH when it spawns this backend,
    pointing at the copy bundled alongside the app (see
    electron/main.js:resolveFfmpegEnv) so users don't need ffmpeg on PATH.
    Falls back to plain 'ffmpeg' (PATH lookup) when running the backend
    standalone (e.g. `python audook_backend.py` outside Electron)."""
    return os.environ.get('AUDOOK_FFMPEG_PATH') or 'ffmpeg'


def get_lan_ip() -> str:
    """This machine's IP on the local network, e.g. "192.168.1.42" - needed
    to build media URLs a Chromecast (a separate device on the LAN) can
    actually reach; "127.0.0.1"/"localhost" only resolve to this same
    machine. Opens no real connection - UDP "connect" just asks the OS
    which local interface would be used to reach that address, which is
    enough to read off the outbound IP without any packets being sent."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_time_short(seconds: float) -> str:
    """Format duration in a short format (MM:SS or H:MM:SS)"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID"""
    import uuid
    return f"{prefix}{uuid.uuid4().hex}"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage"""
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    return sanitized


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def save_json(filepath: Path, data: Any) -> bool:
    """Save data to JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")
        return False


def load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """Load data from JSON file"""
    try:
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        return None


def time_ago(timestamp: datetime) -> str:
    """Get human-readable time ago"""
    now = datetime.now()
    delta = now - timestamp
    
    if delta < timedelta(minutes=1):
        return "Just now"
    elif delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() / 60)}m ago"
    elif delta < timedelta(days=1):
        return f"{int(delta.total_seconds() / 3600)}h ago"
    elif delta < timedelta(days=7):
        return f"{int(delta.days)}d ago"
    elif delta < timedelta(days=30):
        return f"{int(delta.days / 7)}w ago"
    else:
        return f"{int(delta.days / 30)}mo ago"


def get_cache_path(book_id: str, chapter_id: Optional[str] = None) -> Path:
    """Get cache path for a book or chapter"""
    from app import CACHE_DIR
    if chapter_id:
        return CACHE_DIR / f"{book_id}_{chapter_id}.mp3"
    return CACHE_DIR / f"{book_id}.mp3"


def clear_old_cache(max_age_days: int = 30) -> int:
    """Clear old cache files and return count of deleted files"""
    from app import CACHE_DIR
    import time
    
    deleted = 0
    now = time.time()
    max_age = max_age_days * 24 * 60 * 60
    
    for cache_file in CACHE_DIR.glob("*.mp3"):
        if now - cache_file.stat().st_mtime > max_age:
            try:
                cache_file.unlink()
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete cache file: {e}")
    
    return deleted
