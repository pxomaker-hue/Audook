"""
Audook - Audiobook Client for Windows
A modern audiobook player supporting Audiobookshelf and Plex
"""

__version__ = "1.0.0"
__author__ = "Audook Team"
__description__ = "Windows audiobook client for Audiobookshelf and Plex"

from pathlib import Path

# Application paths
APP_NAME = "Audook"
DATA_DIR = Path.home() / f".{APP_NAME}"
CACHE_DIR = DATA_DIR / "cache"
CONFIG_FILE = DATA_DIR / "config.json"
LIBRARY_DB = DATA_DIR / "library.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
