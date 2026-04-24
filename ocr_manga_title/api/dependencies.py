from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.config import load_config
from ocr_manga_title.db.session import async_session_factory
from ocr_manga_title.schemas import AppConfig


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session with automatic commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_config() -> AppConfig:
    """Load and return the application configuration."""
    return load_config()
