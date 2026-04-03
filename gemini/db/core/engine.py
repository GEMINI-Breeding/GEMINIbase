"""
Manages SQLAlchemy database engines and sessions for GEMINI.

This module provides the `DatabaseEngine` class, which encapsulates
the creation, management, and health checking of synchronous and
asynchronous SQLAlchemy engines and session factories. It includes
features like connection pooling, event listeners for monitoring,
and context managers for session handling.
"""

import asyncio
from datetime import datetime
from typing import Generator, Optional, Any
from contextlib import contextmanager, asynccontextmanager
import logging
from sqlalchemy import create_engine, event, exc
from sqlalchemy.sql import text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from gemini.db.config import DatabaseConfig

logger = logging.getLogger(__name__)

class DatabaseEngine:
    """
    Database engine manager with connection pooling, health checks, and monitoring.
    
    Features:
    - Connection pooling with configurable settings
    - Health checks and connection verification
    - Query execution monitoring and logging
    - Support for both sync and async operations
    - Automatic retry on connection failures
    - Connection pool monitoring
    """

    def __init__(self, config: Optional[DatabaseConfig] = None, engine: Optional[Engine] = None, async_engine: Optional[Engine] = None):
        """
        Initialize database engine with configuration.

        Args:
            config (Optional[DatabaseConfig]): Database configuration settings.
            engine (Optional[Engine]): Pre-existing synchronous SQLAlchemy engine.
            async_engine (Optional[Engine]): Pre-existing asynchronous SQLAlchemy engine.

        Raises:
            ValueError: If database configuration is not provided.
        """
        
        if not config:
            raise ValueError("Database configuration is required")
        
        self.config = config 
        self._engine: Optional[Engine] = engine
        self._async_engine = async_engine
        self._session_factory = None
        self._async_session_factory = None
        
        


        # Initialize engines if not provided
        if not self._engine:
            self.setup_engine()
        if not self._async_engine:
            self.setup_async_engine()
        
        # Set up event listeners
        self._setup_engine_events()

    def setup_engine(self) -> None:
        """
        Sets up the synchronous SQLAlchemy engine with optimal settings.

        This method initializes `_engine` and `_session_factory` based on the provided configuration.
        """
        if self._engine is not None:
            return

        self._engine = create_engine(
            self.config.database_url,
            poolclass=self.config.pool_class,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=True,  # Enable connection health checks
            echo=self.config.echo_sql,
            echo_pool=self.config.echo_pool,
            execution_options={
                "isolation_level": self.config.isolation_level
            }
        )

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=True,
            future=True,
            expire_on_commit=False
        )

    def setup_async_engine(self) -> None:
        """
        Sets up the asynchronous SQLAlchemy engine.

        This method initializes `_async_engine` and `_async_session_factory`
        by replacing the 'postgresql' dialect with 'postgresql+asyncpg' in the URL.
        """
        if self._async_engine is not None:
            return
        
        # Add asyncpg dialect to the database URL
        self.config.database_url = self.config.database_url.replace("postgresql", "postgresql+asyncpg")

        self._async_engine = create_async_engine(
            self.config.database_url,
            poolclass=self.config.async_pool_class,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=True,
            echo=self.config.echo_sql,
            echo_pool=self.config.echo_pool
        )

        # Create async session factory
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            autoflush=True,
            expire_on_commit=False
        )

    def get_engine(self) -> Engine:
        """
        Retrieves the synchronous SQLAlchemy engine instance.

        If the engine has not been set up, it calls `setup_engine` to initialize it.

        Returns:
            Engine: The synchronous SQLAlchemy engine.
        """
        return self._engine or self.setup_engine()

    def _setup_engine_events(self) -> None:
        """
        Sets up SQLAlchemy event listeners for monitoring query execution and connection lifecycle.

        This includes logging for `before_cursor_execute`, `after_cursor_execute`,
        `engine_connect`, and `connection_close` events.
        """
        
        @event.listens_for(self._engine, 'before_cursor_execute')
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(datetime.now())
            logger.debug("Executing query: %s", statement)

        @event.listens_for(self._engine, 'after_cursor_execute')
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = datetime.now() - conn.info['query_start_time'].pop()
            logger.debug("Query execution time: %s", total)

        @event.listens_for(self._engine, 'engine_connect')
        def engine_connect(conn):
            logger.debug("New database connection established")

        @event.listens_for(self._engine.pool, 'close')
        def connection_close(dbapi_connection, connection_record):
            logger.debug("Database connection closed")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.
        
        Yields:
            Session: Database session
            
        Example:
            with engine.get_session() as session:
                result = session.query(Model).all()
        """
        session = self._session_factory()
        try:
            yield session
            session.flush()
            session.commit()
        except Exception as e:
            session.rollback()
            # logger.exception("Database session error: %s", str(e))
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> Any:
        """Get an async database session with automatic cleanup.
        
        Yields:
            AsyncSession: Async database session
            
        Example:
            async with engine.get_async_session() as session:
                result = await session.execute(select(Model))
        """
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception("Database session error: %s", str(e))
            raise
        finally:
            await session.close()

    def check_health(self) -> bool:
        """
        Checks the health of the synchronous database connection.

        Executes a simple query to verify connectivity.

        Returns:
            bool: True if the database connection is healthy, False otherwise.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except exc.DBAPIError as e:
            logger.error("Database health check failed: %s", str(e))
            return False

    async def check_health_async(self) -> bool:
        """
        Checks the health of the asynchronous database connection.

        Executes a simple query to verify connectivity.

        Returns:
            bool: True if the async database connection is healthy, False otherwise.
        """
        try:
            async with self._async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except exc.DBAPIError as e:
            logger.error("Async database health check failed: %s", str(e))
            return False

    def get_pool_status(self) -> dict:
        """
        Retrieves the current status and statistics of the synchronous connection pool.

        Returns:
            dict: A dictionary containing pool size, checked-in, checked-out, and overflow statistics.
        """
        return {
            "size": self._engine.pool.size(),
            "checkedin": self._engine.pool.checkedin(),
            "checkedout": self._engine.pool.checkedout(),
            "overflow": self._engine.pool.overflow(),
            "checkedout_overflow": self._engine.pool.overflow()
        }

    def dispose(self) -> None:
        """
        Disposes of both synchronous and asynchronous database engines and their connection pools.

        This method should be called to gracefully shut down database connections.
        """
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            try:
                asyncio.run(self._async_engine.dispose())
            except (ValueError, RuntimeError):
                # greenlet not installed or event loop already running —
                # sync dispose of the underlying engine is sufficient
                self._async_engine.sync_engine.dispose()
