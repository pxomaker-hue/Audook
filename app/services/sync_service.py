"""
Sync service - manages synchronization with servers
"""

from typing import Callable, Optional
import threading
from app.sync import scanner
from app.database import get_session
from app.database.models import Server
from app.utils import logger


class SyncService:
    """Service for managing server synchronization"""

    def __init__(self):
        self._syncing = False
        self._sync_thread: Optional[threading.Thread] = None
        self._on_sync_progress: Optional[Callable[[str, bool], None]] = None

    def sync_all_servers(self, background: bool = False) -> bool:
        """
        Synchronize all configured servers

        Args:
            background: Run in background thread if True
        """
        if background:
            if self._syncing:
                logger.warning("Sync already in progress")
                return False

            self._syncing = True
            self._sync_thread = threading.Thread(target=self._sync_all_servers_sync)
            self._sync_thread.start()
            return True
        else:
            return self._sync_all_servers_sync()

    def _sync_all_servers_sync(self) -> bool:
        """Perform actual sync (runs in thread or main thread)"""
        try:
            session = get_session()
            servers = session.query(Server).filter_by(sync_enabled=True).all()
            session.close()

            if not servers:
                logger.info("No servers configured for synchronization")
                self._notify_progress("No servers configured", False)
                return True

            success_count = 0
            for server in servers:
                try:
                    self._notify_progress(f"Syncing {server.name}...", False)
                    if scanner.scan_server(server):
                        success_count += 1
                        self._notify_progress(f"✓ {server.name} synced", False)
                    else:
                        self._notify_progress(f"✗ Failed to sync {server.name}", False)

                except Exception as e:
                    logger.error(f"Failed to sync server {server.name}: {e}")
                    self._notify_progress(f"✗ {server.name}: {str(e)}", False)

            self._notify_progress(
                f"Sync complete: {success_count}/{len(servers)} servers",
                True
            )

            return success_count == len(servers)

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self._notify_progress(f"Sync failed: {str(e)}", True)
            return False

        finally:
            self._syncing = False

    def sync_server(self, server_id: str) -> bool:
        """Synchronize a specific server"""
        try:
            session = get_session()
            server = session.query(Server).filter_by(id=server_id).first()
            session.close()

            if not server:
                logger.error(f"Server not found: {server_id}")
                return False

            logger.info(f"Syncing server: {server.name}")
            return scanner.scan_server(server)

        except Exception as e:
            logger.error(f"Failed to sync server: {e}")
            return False

    def start_auto_sync(self, interval: int = 3600) -> bool:
        """Start automatic synchronization in background"""
        try:
            logger.info(f"Starting auto-sync with interval {interval}s")
            scanner.start_background_scan(interval)
            return True
        except Exception as e:
            logger.error(f"Failed to start auto-sync: {e}")
            return False

    def stop_auto_sync(self) -> bool:
        """Stop automatic synchronization"""
        try:
            logger.info("Stopping auto-sync")
            scanner.stop_background_scan()
            return True
        except Exception as e:
            logger.error(f"Failed to stop auto-sync: {e}")
            return False

    def is_syncing(self) -> bool:
        """Check if sync is in progress"""
        return self._syncing

    def on_sync_progress(self, callback: Callable[[str, bool], None]):
        """
        Set callback for sync progress

        Args:
            callback: Function(message: str, is_complete: bool)
        """
        self._on_sync_progress = callback

    def _notify_progress(self, message: str, is_complete: bool):
        """Notify progress callback"""
        if self._on_sync_progress:
            try:
                self._on_sync_progress(message, is_complete)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")


# Global instance
sync_service = SyncService()
