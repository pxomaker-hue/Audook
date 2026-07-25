"""
Local audiobook library support
Scan and manage local audiobook folders
"""

from .scanner import LocalAudiobookScanner
from .client import LocalClient

__all__ = ['LocalAudiobookScanner', 'LocalClient']
