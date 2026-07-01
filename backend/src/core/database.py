# core/database.py
"""Minimal database interface - just what we need."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from core.base import Base
from core.models import Job, SourceState, QueryState
from core.config import Config
import logging

logger = logging.getLogger(__name__)

# ================================================================
# Engine Setup
# ================================================================

config = Config.from_env()

engine = create_async_engine(
    config.db_url,
    echo=config.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
async def init_db():
    """Create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ================================================================
# Minimal Database Class
# ================================================================

class Database:
    """Minimal database interface."""

    def __init__(self):
        self._session_factory = AsyncSessionLocal

    async def _session(self) -> AsyncSession:
        """Get a session."""
        return self._session_factory()
    
    


    # ================================================================
    # Sources (URL Registry)
    # ================================================================

    async def get_or_create_source(self, source: str, source_id: str, metadata: Dict = None) -> bool:
        """Add a source if it doesn't exist."""
        session = await self._session()
        try:
            stmt = select(SourceState).where(SourceState.source == source)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return False

            state = SourceState(
                source=source,
                source_id=source_id,
                last_fetch_timestamp=datetime.utcnow(),
                last_fetch_status='pending',
                raw_data=metadata or {}
            )
            session.add(state)
            await session.commit()
            return True
        finally:
            await session.close()

    async def get_stale_sources(self, limit: int = 100, hours: int = 6) -> List[Dict]:
        """Get sources that need scraping."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        session = await self._session()
        try:
            stmt = select(SourceState).where(
                or_(
                    SourceState.last_fetch_timestamp < cutoff,
                    SourceState.last_fetch_timestamp.is_(None)
                )
            ).limit(limit)
            result = await session.execute(stmt)
            sources = result.scalars().all()

            return [
                {
                    'id': s.source_id,
                    'source': s.source,
                    'metadata': s.raw_data or {},
                    'status': s.last_fetch_status,
                }
                for s in sources
            ]
        finally:
            await session.close()

    async def update_source(self, source: str, status: str, job_count: int = 0, metadata: Dict = None):
        """Update a source after scraping."""
        session = await self._session()
        try:
            stmt = select(SourceState).where(SourceState.source == source)
            result = await session.execute(stmt)
            state = result.scalar_one_or_none()
            if state:
                state.last_fetch_timestamp = datetime.utcnow()
                state.last_fetch_status = status
                state.last_fetch_count = job_count
                if metadata:
                    state.raw_data = metadata
                await session.commit()
        finally:
            await session.close()

    # ================================================================
    # Queries (Query Registry)
    # ================================================================

    async def save_query(self, query: str, query_id: str) -> bool:
        """Save a new query."""
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()

        session = await self._session()
        try:
            stmt = select(QueryState).where(QueryState.query_hash == query_hash)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return False

            state = QueryState(
                query_id=query_id,
                query=query,
                query_hash=query_hash,
                status='pending',
            )
            session.add(state)
            await session.commit()
            return True
        finally:
            await session.close()

    async def get_untried_queries(self, limit: int = 20) -> List[Dict]:
        """Get queries not yet tried."""
        session = await self._session()
        try:
            stmt = select(QueryState).where(
                QueryState.times_used == 0
            ).limit(limit)
            result = await session.execute(stmt)
            queries = result.scalars().all()

            return [
                {
                    'id': q.query_id,
                    'query': q.query,
                }
                for q in queries
            ]
        finally:
            await session.close()

    async def update_query(self, query_id: str, success: bool, urls_found: int = 0):
        """Update query after execution."""
        session = await self._session()
        try:
            stmt = select(QueryState).where(QueryState.query_id == query_id)
            result = await session.execute(stmt)
            query = result.scalar_one_or_none()
            if query:
                query.times_used += 1
                query.last_used = datetime.utcnow()
                if success:
                    query.success_count += 1
                    query.status = 'success'
                else:
                    query.failure_count += 1
                    query.status = 'failed'
                if query.raw_data is None:
                    query.raw_data = {}
                query.raw_data['urls_found'] = urls_found
                await session.commit()
        finally:
            await session.close()

    # ================================================================
    # Jobs (Orchestrator)
    # ================================================================

    async def save_jobs(self, jobs: List[Dict]) -> int:
        """Save scraped jobs."""
        if not jobs:
            return 0

        session = await self._session()
        saved = 0
        try:
            for job in jobs:
                stmt = select(Job).where(
                    and_(
                        Job.source == job.get('source', 'unknown'),
                        Job.source_id == job.get('job_id', '')
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.title = job.get('title', existing.title)
                    existing.company = job.get('company', existing.company)
                    existing.location = job.get('location', existing.location)
                    existing.description = job.get('description', existing.description)
                    existing.url = job.get('url', existing.url)
                    existing.posted_at = job.get('posted_at', existing.posted_at)
                else:
                    session.add(Job(
                        source=job.get('source', 'unknown'),
                        source_id=job.get('job_id', ''),
                        title=job.get('title', ''),
                        company=job.get('company', ''),
                        location=job.get('location'),
                        description=job.get('description'),
                        url=job.get('url', ''),
                        posted_at=job.get('posted_at'),
                        raw_data=job.get('raw_data', {})
                    ))
                saved += 1

            await session.commit()
            return saved
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # ================================================================
    # Stats
    # ================================================================

    async def get_stats(self) -> Dict:
        """Get basic stats."""
        session = await self._session()
        try:
            jobs = await session.scalar(select(func.count()).select_from(Job))
            sources = await session.scalar(select(func.count()).select_from(SourceState))
            queries = await session.scalar(select(func.count()).select_from(QueryState))
            return {
                'total_jobs': jobs or 0,
                'total_sources': sources or 0,
                'total_queries': queries or 0,
            }
        finally:
            await session.close()

    # ================================================================
    # Cleanup
    # ================================================================

    async def close(self):
        """Close connections."""
        await engine.dispose()