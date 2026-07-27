"""
Database connection and session management
"""

from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from app.database.models import Base

logger = logging.getLogger(__name__)


class Database:
    """Database manager for Audook"""

    def __init__(self, db_path: str = None):
        """Initialize database"""
        if db_path is None:
            # Default to user data directory
            data_dir = Path.home() / ".audook"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "audook.db")

        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None
        self._init_engine()

    def _init_engine(self):
        """Initialize SQLAlchemy engine"""
        db_url = f"sqlite:///{self.db_path}"
        logger.info(f"Initializing database: {self.db_path}")

        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False  # Set to True for SQL debugging
        )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        """Create all tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        self._run_lightweight_migrations()
        logger.info("Database tables created successfully")

    def _run_lightweight_migrations(self):
        """No migration framework here - create_all only adds missing
        *tables*, not missing *columns* on tables that already exist. Add
        any columns introduced after a table's first release by hand, each
        guarded by a PRAGMA table_info check so it's a no-op on fresh DBs
        (already covered by create_all) and on DBs that already have it."""
        try:
            with self.engine.connect() as conn:
                columns = {row[1] for row in conn.execute(text("PRAGMA table_info(servers)"))}
                if "remote_url" not in columns:
                    conn.execute(text("ALTER TABLE servers ADD COLUMN remote_url VARCHAR(500)"))
                    logger.info("Migrated: added servers.remote_url")
                if "use_remote" not in columns:
                    conn.execute(text("ALTER TABLE servers ADD COLUMN use_remote BOOLEAN DEFAULT 0"))
                    logger.info("Migrated: added servers.use_remote")
                if "hidden" not in columns:
                    conn.execute(text("ALTER TABLE servers ADD COLUMN hidden BOOLEAN DEFAULT 0"))
                    logger.info("Migrated: added servers.hidden")
                conn.commit()
        except Exception as e:
            logger.error(f"Lightweight migration failed: {e}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database closed")

    def reset_db(self):
        """Drop all tables and recreate (for development)"""
        logger.warning("Resetting database...")
        Base.metadata.drop_all(bind=self.engine)
        self.init_db()
        logger.info("Database reset complete")


# Global database instance
_db: Database = None


def init_database(db_path: str = None):
    """Initialize global database"""
    global _db
    _db = Database(db_path)
    _db.init_db()
    return _db


def get_db() -> Database:
    """Get global database instance"""
    global _db
    if _db is None:
        _db = init_database()
    return _db


def get_session() -> Session:
    """Get a new database session from global instance"""
    return get_db().get_session()
