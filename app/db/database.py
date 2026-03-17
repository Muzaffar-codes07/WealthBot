"""
WealthBot Database Connection Module
=====================================
Async PostgreSQL connection using SQLAlchemy 2.0 with Singleton pattern.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton Database Manager for async PostgreSQL connections.
    
    Implements the Singleton pattern to ensure only one engine instance
    exists throughout the application lifecycle.
    
    Usage:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        async with db_manager.session() as session:
            result = await session.execute(query)
    """

    _instance: Optional["DatabaseManager"] = None
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def _is_sqlite(self) -> bool:
        """Check if the configured database is SQLite."""
        return settings.database_url.startswith("sqlite")

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine, creating if necessary."""
        if self._engine is None:
            kwargs: dict = {
                "echo": settings.debug,
                "future": True,
            }
            if self._is_sqlite:
                kwargs["connect_args"] = {"check_same_thread": False}
            else:
                kwargs.update(
                    pool_size=settings.db_pool_size,
                    max_overflow=settings.db_max_overflow,
                    pool_timeout=settings.db_pool_timeout,
                    pool_pre_ping=True,
                )
            self._engine = create_async_engine(settings.database_url, **kwargs)
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory, creating if necessary."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return self._session_factory

    async def initialize(self) -> None:
        """
        Initialize the database connection pool.
        
        Should be called during application startup.
        """
        if self._initialized:
            logger.info("Database already initialized")
            return

        logger.info("Initializing database connection pool...")

        # Auto-create tables for SQLite (dev convenience)
        if self._is_sqlite:
            from app.db.models import Base

            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("SQLite tables created / verified")

        # Verify connection by executing a simple query
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                logger.info("Database connection verified successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

        self._initialized = True
        logger.info("Database initialization complete")

    async def close(self) -> None:
        """
        Close all database connections.
        
        Should be called during application shutdown.
        """
        if self._engine is not None:
            logger.info("Closing database connection pool...")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            logger.info("Database connections closed")

    async def health_check(self) -> bool:
        """
        Perform a database health check.
        
        Returns:
            True if database is reachable, False otherwise
        """
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def session(self) -> AsyncSession:
        """
        Get a new async session.
        
        Usage:
            async with db_manager.session() as session:
                # Use session
        """
        return self.session_factory()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get a database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    db_manager = DatabaseManager()
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
