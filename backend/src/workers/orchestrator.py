# orchestrator.py
"""Orchestrator - Coordinates services via direct function calls."""

import asyncio
import time
import logging

from browser_pool import BrowserPool
from worker_pool import WorkerPool
from components.redis_queue import RedisQueue
from core.config import Config
from data_sources.url_registry import URLRegistry
from modules.llm_discovery import LLMDiscovery
from modules.result_aggregator import ResultAggregator
from modules.database import Database

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Coordinates everything via direct function calls.
    No HTTP, no JSON, just clean Python.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Core components
        self.redis = RedisQueue(config)
        self.url_registry = URLRegistry(config.db_url)
        self.llm_discovery = LLMDiscovery(config.llm_api_key, config.llm_model)
        self.aggregator = ResultAggregator()
        self.db = Database(config.db_url)
        
        # Services - they call each other directly
        self.browser_service = BrowserService(config)
        self.worker_service = WorkerService(config, self.browser_service, self.redis)
        
        self.is_running = False
    
    async def run_once(self, num_workers: int = 4):
        """Run a single scraping cycle."""
        logger.info("🔄 Starting scraping cycle...")
        if self.config.enable_discovery:
            await self._discover_new_sources()
        urls = self.url_registry.get_urls_to_scrape(
            limit=self.config.max_urls_per_cycle
        )
        
        if not urls:
            logger.info("No URLs to scrape")
            return
        

        self.redis.push_tasks(urls)
        await self.browser_service.start()
        await self.worker_service.start(num_workers)
        results = self.redis.pop_all_results()
        
        jobs = self.aggregator.aggregate(results)
        self.db.save_jobs(jobs)
        
        for result in results:
            self.url_registry.update_status(
                url_id=result.get("url_id"),
                success=result.get("success", False),
                job_count=len(result.get("jobs", []))
            )
        await self.worker_service.stop()
        await self.browser_service.stop()
        
        logger.info(f"✅ Cycle complete: {len(jobs)} jobs saved")
    
    async def run_continuous(self):
        """Run orchestrator continuously."""
        self.is_running = True
        logger.info("🚀 Orchestrator running continuously")
        
        while self.is_running:
            try:
                await self.run_once(
                    num_workers=self.config.workers_per_cycle
                )
                logger.info(f"⏰ Sleeping for {self.config.cycle_interval_hours} hours...")
                await asyncio.sleep(self.config.cycle_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
                await asyncio.sleep(60)
    
    async def _discover_new_sources(self):
        """Run LLM discovery."""
        # ... implementation ...
        pass
    
    async def stop(self):
        """Stop everything."""
        self.is_running = False
        await self.worker_service.stop()
        await self.browser_service.stop()
        logger.info("🛑 Orchestrator stopped")