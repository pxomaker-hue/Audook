#!/usr/bin/env python3
"""
Audook - Audiobook Player
Main application entry point
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication

from app.database import init_database
from app.ui import MainWindow
from app.utils import logger


def main():
    """Main application entry point"""
    logger.info("Starting Audook...")

    # Initialize database
    logger.info("Initializing database...")
    init_database()

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Audook ready")

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
