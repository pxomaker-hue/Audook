#!/usr/bin/env python3
"""
Audook - Audiobook Client for Windows
A modern audiobook player supporting Audiobookshelf and Plex

Usage:
 python main.py
"""

import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QEventLoop
from qasync import QEventLoop as AsyncioEventLoop

from app.main_window import MainWindow
from app.utils.config_manager import config_manager


def main():
    """Main entry point"""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Audook")
    app.setOrganizationName("Audook Team")

    # Create async event loop for Qt
    loop = AsyncioEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Execute application with async event loop
    with loop:
        sys.exit(loop.run_forever())


if __name__ == "__main__":
    main()
