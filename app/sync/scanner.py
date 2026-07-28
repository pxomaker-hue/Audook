"""
Server scanner for audiobook discovery and synchronization
Scans Plex and Audiobookshelf servers and updates database
"""

from typing import Optional, List
from datetime import datetime
import threading
import time
import asyncio

from app.database import get_session, ServerRepository, BookRepository, BookmarkRepository, ReadingProgressRepository
from app.database.models import Server, Library, Book, ReadingProgress
from app.clients import PlexClient, AudiobookshelfClient
from app.local import LocalClient
from app.sync import progress_sync
from app.utils import logger, online_metadata


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
            elif server.type == "local":
                return self._scan_local(server)
            else:
                logger.error(f"Unknown server type: {server.type}")
                return False

        except Exception as e:
            logger.error(f"Failed to scan server {server.name}: {e}")
            return False

    def _enrich_with_online_metadata(self, title, author, description, cover_url, extra_metadata):
        """Fill gaps left by the source server using online lookups (Wikipedia for
        author bio/photo, Open Library for book description/cover). Never
        overwrites data the server already provided."""
        extra_metadata = dict(extra_metadata or {})

        if not extra_metadata.get("author_bio") or not extra_metadata.get("author_photo"):
            author_info = online_metadata.fetch_author_info_online(author)
            if not extra_metadata.get("author_bio"):
                extra_metadata["author_bio"] = author_info.get("bio")
            if not extra_metadata.get("author_photo"):
                extra_metadata["author_photo"] = author_info.get("photo")

        if not description or not cover_url:
            book_info = online_metadata.fetch_book_info_online(title, author)
            if not description:
                description = book_info.get("description")
            if not cover_url:
                cover_url = book_info.get("cover_url")

        return description, cover_url, extra_metadata

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
                        description, cover_url, extra_metadata = self._enrich_with_online_metadata(
                            audiobook["title"], audiobook.get("author"), audiobook.get("description"),
                            audiobook.get("cover_url"), audiobook.get("extra_metadata")
                        )
                        book_repo.create(
                            book_id=audiobook["id"],
                            server_id=server.id,
                            library_id=lib_id,
                            title=audiobook["title"],
                            author=audiobook.get("author"),
                            narrator=audiobook.get("narrator"),
                            description=description,
                            duration=audiobook["duration"],
                            chapters=audiobook.get("chapters", []),
                            cover_url=cover_url,
                            extra_metadata=extra_metadata
                        )
                        logger.info(f"Added Plex audiobook: {audiobook['title']}")
                        self._seed_remote_progress_if_new(session, server, client, audiobook["id"])
                    except Exception as e:
                        logger.warning(f"Failed to add audiobook {audiobook.get('title')}: {e}")

            session.commit()

            # Update server sync time (own session/commit, since `server` may belong to a closed session)
            ServerRepository(session).update_sync_timestamp(server.id)
            session.close()

            logger.info(f"Plex scan complete for server: {server.name}")
            return True

        except Exception as e:
            logger.error(f"Plex scan failed: {e}")
            return False

    def _scan_audiobookshelf(self, server: Server) -> bool:
        """Scan Audiobookshelf server"""
        try:
            client = AudiobookshelfClient(
                ServerRepository.active_url(server),
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
                        description, cover_url, extra_metadata = self._enrich_with_online_metadata(
                            audiobook["title"], audiobook.get("author"), audiobook.get("description"),
                            audiobook.get("cover_url"), audiobook.get("extra_metadata")
                        )
                        book_repo.create(
                            book_id=audiobook["id"],
                            server_id=server.id,
                            library_id=lib_data["id"],
                            title=audiobook["title"],
                            author=audiobook.get("author"),
                            narrator=audiobook.get("narrator"),
                            description=description,
                            duration=audiobook["duration"],
                            chapters=audiobook.get("chapters", []),
                            cover_url=cover_url,
                            extra_metadata=extra_metadata
                        )
                        logger.info(f"Added Audiobookshelf audiobook: {audiobook['title']}")
                        self._seed_remote_progress_if_new(session, server, client, audiobook["id"])
                    except Exception as e:
                        logger.warning(f"Failed to add audiobook {audiobook.get('title')}: {e}")

            session.commit()

            # Update server sync time (own session/commit, since `server` may belong to a closed session)
            ServerRepository(session).update_sync_timestamp(server.id)
            session.close()

            logger.info(f"Audiobookshelf scan complete for server: {server.name}")
            return True

        except Exception as e:
            logger.error(f"Audiobookshelf scan failed: {e}")
            return False

    def _seed_remote_progress_if_new(self, session, server: Server, client, book_id: str):
        """A book that already has partial listening progress recorded on
        its source server (e.g. played via the Audiobookshelf app/web player
        before ever being opened in Audook) previously only had that
        progress pulled in on first playback - meaning it never showed up
        under "Reprendre l'écoute" until then. Seed it right away on scan
        instead, but only if there's no local progress yet, so a re-scan
        never clobbers what the user has done locally since.

        Reuses the scan's own already-authenticated `client` instead of
        going through progress_sync.pull_progress(), which builds a brand
        new client (and re-logs in) per call - fired once per book, that
        hammered Audiobookshelf's /login endpoint hard enough to get rate
        limited (HTTP 429) partway through a ~60-book library."""
        # get_or_create() (called e.g. every time the book detail page is
        # opened, via GET /api/books/<id>) silently creates a blank
        # ReadingProgress row with everything at zero - that's not the same
        # thing as "the user has real local progress" and must not block
        # seeding, or the real remote progress could never be pulled in for
        # any book that had merely been viewed once.
        existing = session.query(ReadingProgress).filter_by(book_id=book_id).first()
        if existing and (existing.progress_percent > 0 or existing.position_seconds > 0 or existing.is_finished):
            return
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return
        if (book.extra_metadata or {}).get("progress_dismissed"):
            return
        try:
            if server.type == "plex":
                remote = client.pull_progress(book_id, book.chapters or [])
            elif server.type == "audiobookshelf":
                item_id = book_id.replace("abs_", "", 1)
                raw = client.get_user_progress(item_id)
                if not raw:
                    remote = None
                else:
                    chapter_index, position = progress_sync._split_cumulative(
                        book.chapters or [], raw.get("position_seconds", 0.0)
                    )
                    remote = {"chapter_index": chapter_index, "position_seconds": position, "finished": raw.get("finished", False)}
            else:
                remote = None
        except Exception as e:
            logger.warning(f"Failed to pull remote progress for {book_id}: {e}")
            return
        if not remote:
            return

        duration = (book.duration if book else 0) or 0
        if duration <= 0:
            return
        cumulative = 0.0
        for i, chapter in enumerate(book.chapters or []):
            if i < remote["chapter_index"]:
                cumulative += chapter.get("duration", 0) or 0
            elif i == remote["chapter_index"]:
                cumulative += remote["position_seconds"]
                break
        percent = 100.0 if remote.get("finished") else min(100.0, (cumulative / duration) * 100)
        if percent <= 0:
            return

        ReadingProgressRepository(session).update_progress(
            book_id, remote["chapter_index"], remote["position_seconds"], percent
        )
        if remote.get("finished"):
            ReadingProgressRepository(session).set_finished(book_id, True)
        logger.info(f"Seeded remote progress for {book_id}: {percent:.1f}%")

    def _delete_local_book_if_safe(self, session, book_id: str) -> bool:
        """Delete a local book row unless it has reading progress or
        bookmarks tied to it, so nothing the user did gets lost. Returns
        whether it was deleted."""
        from app.database.models import ReadingProgress

        book_repo = BookRepository(session)
        bookmark_repo = BookmarkRepository(session)

        # Query directly (not via get_or_create) - that helper creates an
        # empty progress row as a side effect, which would pollute the DB
        # with rows for every book just from checking this.
        existing_progress = session.query(ReadingProgress).filter_by(book_id=book_id).first()
        has_progress = bool(existing_progress and existing_progress.progress_percent > 0)
        has_bookmarks = len(bookmark_repo.get_by_book(book_id)) > 0
        if has_progress or has_bookmarks:
            logger.info(f"Keeping local duplicate '{book_id}' - it has reading progress or bookmarks")
            return False

        book_repo.delete(book_id)
        return True

    def _cleanup_existing_local_duplicates(self, session, local_server_id: str) -> int:
        """Remove local-folder books left over from *before* the dedup
        check in _scan_local existed, that duplicate a book from a real
        server - only when it's safe to do so (see _delete_local_book_if_safe)."""
        book_repo = BookRepository(session)

        local_books = book_repo.get_by_server(local_server_id)
        removed = 0
        for local_book in local_books:
            duplicate = book_repo.find_existing_from_other_source(
                local_book.title, local_book.author, local_server_id
            )
            if not duplicate:
                continue
            if self._delete_local_book_if_safe(session, local_book.id):
                removed += 1

        return removed

    def _scan_local(self, server: Server) -> bool:
        """Scan a local audiobook folder"""
        try:
            client = LocalClient(server.url)

            if not asyncio.run(client.ping()):
                logger.error(f"Local folder not accessible: {server.url}")
                return False

            lib_id = f"local_{server.id}"
            audiobooks = asyncio.run(client.get_audiobooks(lib_id, limit=10000))

            session = get_session()
            book_repo = BookRepository(session)
            skipped_duplicates = 0

            for audiobook in audiobooks:
                try:
                    # Skip books already present from a real server (Plex/
                    # Audiobookshelf) - very common when the local folder
                    # points at the same NAS path those already scan, and
                    # those sources have much richer metadata (series,
                    # genres, proper covers) that a plain folder scan can't
                    # match. Prevents the same book showing up twice with
                    # inconsistent metadata between the two copies.
                    duplicate = book_repo.find_existing_from_other_source(
                        audiobook.title, audiobook.author, server.id
                    )
                    if duplicate:
                        skipped_duplicates += 1
                        logger.info(
                            f"Skipped local duplicate of '{audiobook.title}' "
                            f"(already present from server {duplicate.server_id})"
                        )
                        # A pre-existing DB row for this same local book may
                        # already exist with stale data from before it was
                        # recognized as a duplicate (e.g. author metadata
                        # that has since been extracted more accurately) -
                        # remove it now rather than leaving it stuck with
                        # outdated info forever, since it'll never go
                        # through book_repo.create() again to refresh it.
                        self._delete_local_book_if_safe(session, audiobook.id)
                        continue

                    description, cover_url, extra_metadata = self._enrich_with_online_metadata(
                        audiobook.title, audiobook.author, audiobook.description, audiobook.cover, None
                    )
                    book_repo.create(
                        book_id=audiobook.id,
                        server_id=server.id,
                        library_id=lib_id,
                        title=audiobook.title,
                        author=audiobook.author,
                        narrator=audiobook.narrator,
                        description=description,
                        duration=audiobook.duration,
                        chapters=audiobook.chapters,
                        cover_url=cover_url,
                        extra_metadata=extra_metadata
                    )
                    logger.info(f"Added local audiobook: {audiobook.title}")
                except Exception as e:
                    logger.warning(f"Failed to add audiobook {audiobook.title}: {e}")

            if skipped_duplicates:
                logger.info(f"Local scan skipped {skipped_duplicates} book(s) already present from another server")

            session.commit()

            # One-time cleanup: remove local duplicates created by *earlier*
            # scans, before this dedup check existed - only when it's safe
            # to do so (no reading progress or bookmarks tied to that
            # specific local copy, so nothing is lost).
            removed_duplicates = self._cleanup_existing_local_duplicates(session, server.id)
            if removed_duplicates:
                logger.info(f"Removed {removed_duplicates} pre-existing local duplicate(s)")

            ServerRepository(session).update_sync_timestamp(server.id)
            session.close()

            logger.info(f"Local scan complete for: {server.name}")
            return True

        except Exception as e:
            logger.error(f"Local scan failed: {e}")
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
