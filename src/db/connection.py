"""Database connection management with PostgreSQL and SQLite fallback."""

import os
from typing import Tuple
from loguru import logger
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.db.models import Base

DEFAULT_SQLITE_URL = "sqlite:///elyra.db"


def get_engine() -> Tuple[Engine, str]:
    """Obtain SQLAlchemy engine. Attempts PostgreSQL first, falls back to SQLite."""
    pg_url = os.getenv("DATABASE_URL")
    if pg_url:
        try:
            engine = create_engine(pg_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to primary PostgreSQL database.")
            return engine, "PostgreSQL"
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite.")

    # SQLite Fallback
    engine = create_engine(DEFAULT_SQLITE_URL, connect_args={"check_same_thread": False})
    logger.info(f"Using SQLite database ({DEFAULT_SQLITE_URL}).")
    return engine, "SQLite"


def init_db(engine: Engine):
    """Create all tables in the connected database."""
    try:
        Base.metadata.create_all(engine, checkfirst=True)
        logger.info("Initialized database schema.")
    except Exception as e:
        logger.warning(f"Database schema initialization notice: {e}")


def get_session(engine: Engine) -> Session:
    """Create a new database session."""
    session_factory = sessionmaker(bind=engine)
    return session_factory()

