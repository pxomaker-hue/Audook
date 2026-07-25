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
from PyQt6.QtCore import QTimer

from app.main_window import MainWindow
from app.utils.config_manager import config_manager


def main():
 """Main entry point"""
 # Create QApplication
 app = QApplication(sys.argv)
 app.setApplicationName("Audook")
 app.setOrganizationName("Audook Team")
 
 # Create and show main window
 window = MainWindow()
 window.show()
 
 # Start async event loop
 loop = asyncio.new_event_loop()
 asyncio.set_event_loop(loop)
 
 # Run a timer to process async tasks
 timer = QTimer()
 timer.timeout.connect(lambda: loop.run_until_complete(asyncio.sleep(0)))
 timer.start(100)
 
 # Execute application
 sys.exit(app.exec())


if __name__ == "__main__":
 main()
