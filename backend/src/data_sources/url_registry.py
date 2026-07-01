# data_sources/url_registry.py
"""URL Registry - thin layer on Database."""

import hashlib
from datetime import datetime
from typing import List, Dict, Optional
import logging

from core.database import Database

logger = logging.getLogger(__name__)


class URLRegistry:
    def __init__(self, db: Database):
        self.db = db

    async def add_url(self, url: str, source: str, company: str = None, metadata: Dict = None) -> str:
        source_id = hashlib.md5(url.encode()).hexdigest()[:16]
        await self.db.get_or_create_source(source, source_id, {
            'url': url,
            'company': company or 'Unknown',
            **(metadata or {})
        })
        return source_id

    async def get_urls_to_scrape(self, limit: int = 100) -> List[Dict]:
        sources = await self.db.get_stale_sources(limit)
        return [
            {
                'id': s['id'],
                'source': s['source'],
                'url': s['metadata'].get('url', ''),
                'company': s['metadata'].get('company', 'Unknown'),
            }
            for s in sources
        ]

    async def update_status(self, source: str, success: bool, job_count: int = 0):
        await self.db.update_source(source, 'success' if success else 'failed', job_count)