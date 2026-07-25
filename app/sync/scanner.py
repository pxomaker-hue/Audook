"""
Server scanner for audiobook discovery and synchronization
Scans Plex and Audiobookshelf servers and updates database
"""

from typing import Optional, List
from datetime import datetime
import threading
import time

from app.database import get_session, ServerRepository, BookRepository
from app.database.models import Server, Library, Book
from app.clients import PlexClient, AudiobookshelfClient
from app.utils import logger


class ServerScanner:
    """Scans servers for audiobooks and syncs with database"""

    def __init__(self):
        self._scanning = False
        self._scan_thread: Optional[threading.Thread] = None

    def scan_server(self, server: Server) -> bool:
        """Scan a single server for audiobooks"""
        try:
            logger.info(f"Scanning server: {server.name}")

            if server.type == "plex":
                return self._scan_plex(server)
            elif server.type == "audiobookshelf":
                return self._scan_audiobookshelf(server)
            else:
                logger.error(f"Unknown server type: {server.type}")
                return False

        except Exception as e:
            logger.error(f"Failed to scan server {server.name}: {e}")
            return False

    def _scan_plex(self, server: Server) -> bool:
        """Scan Plex server"""
        try:
            client = PlexClient(server.url, server.api_key)

            if not client.test_connection():
                logger.error(f"Failed to connect to Plex server: {server.name}")
                return False

            # Get libraries
            plex_libraries = client.get_audiobook_libraries()

            session = get_session()
            book_repo = BookRepository(session)

            for lib_data in plex_libraries:
                # Create or update library in database
                lib_id = f"plex_{server.id}_{lib_data['id']}"

                # Get audiobooks from library
                audiobooks = client.get_audiobooks(lib_data["id"])

                for audiobook in audiobooks:
                    try:
                        book_repo.create(
                            book_id=audiobook["id"],
                            server_id=server.id,
                            library_id=lib_id,
                            title=audiobook["title"],
                            author=audiobook.get("author"),
                            narrator=audiobook.get("narrator"),
                            duration=audiobook["duration"],
                            chapters=audiobook.get("chapters", []),
                            cover_url=audiobook.get("cover_url")
                        )
                        logger.info(f"Added Plex audiobook: {audiobook['title']}")
                    except Exception as e:
                        logger.warning(f"Failed to add audiobook {audiobook.get('title')}: {e}")

            session.commit()
            session.close()

            # Update server sync time
            server.last_sync = datetime.utcnow()

            logger.info(f"Plex scan complete for server: {server.name}")
            return True

        except Exception as e:
            logger.error(f"Plex scan failed: {e}")
            return False

    def _scan_audiobookshelf(self, server: Server) -> bool:
        """Scan Audiobookshelf server"""
        try:
            client = AudiobookshelfClient(
                server.url,
                server.username,
                server.password
            )

            if not client.test_connection():
                logger.error(f"Failed to connect to Audiobookshelf server: {server.name}")
                return False

            # Get libraries
            libraries = client.get_libraries()

            session = get_session()
            book_repo = BookRepository(session)

            for lib_data in libraries:
                # Get audiobooks from library
                audiobooks = client.get_audiobooks(lib_data["id"])

                for audiobook in audiobooks:
                    try:
                        book_repo.create(
                            book_id=audiobook["id"],
                            server_id=server.id,
                            library_id=lib_data["id"],
                            title=audiobook["title"],
                            author=audiobook.get("author"),
                            narrator=audiobook.get("narrator"),
                            duration=audiobook["duration"],
                            chapters=audiobook.get("chapters", []),
                            cover_url=audiobook.get("cover_url"),
                            extra_metadata=audiobook.get("extra_metadata")
                        )
                        logger.info(f"Added Audiobookshelf audiobook: {audiobook['title']}")
                    except Exception as e:
                        logger.warning(f"Failed to add audiobook {audiobook.get('title')}: {e}")

            session.commit()
            session.close()

            # Update server sync time
            server.last_sync = datetime.utcnow()

            logger.info(f"Audiobookshelf scan complete for server: {server.name}")
            return True

        except Exception as e:
            logger.error(f"Audiobookshelf scan failed: {e}")
            return False

    def scan_all_servers(self) -> bool:
        """Scan all enabled servers"""
        try:
            session = get_session()
            server_repo = ServerRepository(session)

            servers = session.query(Server).filter(Server.sync_enabled == True).all()

            if not servers:
                logger.info("No servers configured for scanning")
                return True

            success_count = 0
            for server in servers:
                if self.scan_server(server):
                    success_count += 1

            session.close()

            logger.info(f"Scan complete: {success_count}/{len(servers)} servers scanned successfully")
            return success_count == len(servers)

        except Exception as e:
            logger.error(f"Failed to scan all servers: {e}")
            return False

    def start_background_scan(self, interval: int = 3600):
        """Start background scanning thread (default 1 hour)"""
        if self._scanning:
            logger.warning("Scanner already running")
            return

        self._scanning = True
        self._scan_thread = threading.Thread(
            target=self._background_scan_loop,
            args=(interval,),
            daemon=True
        )
        self._scan_thread.start()
        logger.info(f"Background scanner started (interval: {interval}s)")

    def _background_scan_loop(self, interval: int):
        """Continuously scan servers at specified interval"""
        while self._scanning:
            try:
                self.scan_all_servers()
            except Exception as e:
                logger.error(f"Background scan error: {e}")

            time.sleep(interval)

    def stop_background_scan(self):
        """Stop background scanning thread"""
        self._scanning = False
        if self._scan_thread:
            self._scan_thread.join(timeout=5.0)
        logger.info("Background scanner stopped")


# Global scanner instance
scanner = ServerScanner()
