"""
Database session factory.

Provides async SQLAlchemy session management for FastAPI.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.config import server_config
from server.db.models import Base

engine = create_async_engine(server_config.database_url, echo=server_config.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        try:
            yield session  # type: ignore[misc]
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close the database engine."""
    await engine.dispose()
