# WORKFLOW: Database session management and connection handling.
# Used by: All database operations throughout the application
# Functions:
# 1. get_db() - Dependency injection for FastAPI endpoints
# 2. init_db() - Initialize database tables and schemas
# 3. check_db_connection() - Health check for database connectivity
#
# Database lifecycle:
# Startup: init_db() -> Create tables -> Check connection
# Runtime: get_db() -> Session -> Query -> Close session
# Health checks: check_db_connection() -> Monitor connectivity

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Lazy-loaded database engine and session factory
_engine = None
_SessionLocal = None

def get_engine():
    """Get database engine (lazy-loaded)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            poolclass=StaticPool,
            pool_pre_ping=True,
            echo=settings.debug,
            connect_args={
                "options": "-c timezone=utc"
            }
        )
    return _engine

def get_session_factory():
    """Get session factory (lazy-loaded)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    """
    Dependency to get database session.
    Yields a database session and ensures it's closed after use.
    """
    logger.info("Creating database session...")
    SessionLocal = get_session_factory()
    db = SessionLocal()
    logger.info("Database session created successfully")
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


def init_db():
    """
    Initialize database tables.
    """
    from db.models import Base
    
    try:
        # Create all tables
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Create text_index schema if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS text_index"))
            conn.commit()
        logger.info("Text index schema created successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
