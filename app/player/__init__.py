"""
Audio player module
VLC-based player with progress tracking and database persistence
"""

from app.player.vlc_player import VLCPlayer, player
from app.player.progress_manager import ProgressManager, progress_manager
from app.player.queue import queue
from app.player.output_router import OutputRouter, active_output

__all__ = [
    "VLCPlayer",
    "player",
    "ProgressManager",
    "progress_manager",
    "queue",
    "OutputRouter",
    "active_output",
]
