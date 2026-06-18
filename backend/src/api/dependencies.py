"""Reusable API dependencies."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db


async def get_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Return the current database session dependency."""

    return db
