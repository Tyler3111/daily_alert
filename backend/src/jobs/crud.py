"""CRUD placeholders for jobs."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Job


async def get_jobs(db: AsyncSession) -> list[Job]:
    """Return placeholder job query results."""

    _ = db
    return []
