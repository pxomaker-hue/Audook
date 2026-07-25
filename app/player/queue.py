"""
Playback queue for Audook
Manages the queue of audiobooks/chapters to play
"""

from typing import List, Dict, Any, Optional
from app.models import Audiobook


class PlaybackQueue:
    """Manages the playback queue"""
    
    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
        self._current_index: int = -1
        self._repeat: bool = False
        self._shuffle: bool = False
    
    def add(self, audiobook: Audiobook, chapter: Dict[str, Any]):
        """Add an item to the queue"""
        self._queue.append({
            "audiobook": audiobook,
            "chapter": chapter
        })
    
    def add_audiobook(self, audiobook: Audiobook):
        """Add all chapters of an audiobook to the queue"""
        for chapter in audiobook.chapters:
            self.add(audiobook, chapter)
    
    def clear(self):
        """Clear the queue"""
        self._queue.clear()
        self._current_index = -1
    
    def remove(self, index: int) -> bool:
        """Remove an item from the queue"""
        if 0 <= index < len(self._queue):
            if index < self._current_index:
                self._current_index -= 1
            elif index == self._current_index:
                self._current_index = -1
            
            self._queue.pop(index)
            return True
        return False
    
    def get_current(self) -> Optional[Dict[str, Any]]:
        """Get the current item"""
        if self._current_index >= 0 and self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None
    
    def get_next(self) -> Optional[Dict[str, Any]]:
        """Get the next item"""
        if len(self._queue) == 0:
            return None
        
        if self._current_index < 0:
            # Start from beginning
            self._current_index = 0
            return self._queue[0]
        
        if self._current_index + 1 < len(self._queue):
            self._current_index += 1
            return self._queue[self._current_index]
        
        if self._repeat:
            self._current_index = 0
            return self._queue[0]
        
        return None
    
    def get_previous(self) -> Optional[Dict[str, Any]]:
        """Get the previous item"""
        if len(self._queue) == 0:
            return None
        
        if self._current_index <= 0:
            if self._repeat:
                self._current_index = len(self._queue) - 1
                return self._queue[self._current_index]
            return None
        
        self._current_index -= 1
        return self._queue[self._current_index]
    
    def set_current(self, index: int) -> bool:
        """Set the current item by index"""
        if 0 <= index < len(self._queue):
            self._current_index = index
            return True
        return False
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all items in the queue"""
        return self._queue.copy()
    
    def size(self) -> int:
        """Get the size of the queue"""
        return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self._queue) == 0
    
    def set_repeat(self, repeat: bool):
        """Set repeat mode"""
        self._repeat = repeat
    
    def set_shuffle(self, shuffle: bool):
        """Set shuffle mode"""
        self._shuffle = shuffle
        if shuffle:
            import random
            random.shuffle(self._queue)
    
    def get_current_index(self) -> int:
        """Get current index"""
        return self._current_index


# Global queue instance
queue = PlaybackQueue()
