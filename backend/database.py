"""
PostgreSQL Database Infrastructure using SQLAlchemy 2.x.
Provides engine creation, session factory, base declarative model,
and FastAPI dependency injection for session management.
"""

import os
import logging
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("Database")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASSWORD", "postgres")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "accessibility_auditor")
    DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    logger.info(f"DATABASE_URL not set; using derived fallback: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")

pool_size = int(os.environ.get("DB_POOL_SIZE", 5))
max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", 10))

# Configure connection pool
# Note: SQLAlchemy pool_pre_ping tests connection liveness before checking out from pool
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined on Base metadata."""
    try:
        # Import models here so that they are registered with Base.metadata before creating
        import backend.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        raise


def check_db_connection() -> bool:
    """Check if the database engine can execute a simple SELECT 1 query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connectivity check failed: {e}")
        return False
