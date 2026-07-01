# data_sources/query_registry.py
"""Query Registry - thin layer on Database."""

import hashlib
from typing import List, Dict
import logging

from core.database import Database

logger = logging.getLogger(__name__)


class QueryRegistry:
    def __init__(self, db: Database):
        self.db = db

    async def add_query(self, query: str) -> str:
        query_id = f"q_{hashlib.md5(query.encode()).hexdigest()[:12]}"
        await self.db.save_query(query, query_id)
        return query_id

    async def get_untried_queries(self, limit: int = 20) -> List[Dict]:
        return await self.db.get_untried_queries(limit)

    async def update_status(self, query_id: str, success: bool, urls_found: int = 0):
        await self.db.update_query(query_id, success, urls_found)
    
    
