# orchestrator.py
"""Orchestrator - Coordinates services via direct function calls."""

import asyncio
import time
import logging
from datetime import datetime

from .browser_pool import BrowserPool
from .worker_pool import WorkerPool
from components.redis_queue import RedisQueue
from core.config import Config
from data_sources.url_registry import URLRegistry
from data_sources.discovery_engine import DiscoveryEngine
from scraper.result_aggregator import ResultAggregator
from core.database import Database,init_db
from data_sources.query_registry import QueryRegistry

logger = logging.getLogger(__name__)

class Orchestrator:
    """Coordinates everything — discovery, scraping, and scheduling."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Database
        self.db = Database()
        
        # Registries
        self.url_registry = URLRegistry(self.db)
        self.query_registry = QueryRegistry(self.db)
        
        # Discovery Engine (LLM + search orchestration)
        self.discovery_engine = DiscoveryEngine(
            config=config,
            url_registry=self.url_registry,
            query_registry=self.query_registry
        )
        
        # Redis
        self.redis = RedisQueue(config)
        
        # Services
        self.browser_service = BrowserPool(config)
        self.worker_service = WorkerPool(
            config=config,
            browser_service=self.browser_service,
            redis_component=self.redis
        )
        
        self.is_running = False
    
    # ================================================================
    # Discovery
    # ================================================================
    
    async def run_discovery_cycle(self):
        """Run discovery to find new job sources."""
        return await self.discovery_engine.run_discovery_cycle()
    
    # ================================================================
    # Scraping
    # ================================================================
    
    async def run_scraping_cycle(self, num_workers: int = 4):
        """Run scraping cycle on discovered URLs."""
        logger.info("🔄 Starting scraping cycle...")
        
        # Get URLs to scrape
        urls = await self.url_registry.get_urls_to_scrape(
            limit=self.config.max_urls_per_cycle
        )
        
        if not urls:
            logger.info("No URLs to scrape")
            return
        
        # Push tasks to Redis
        self.redis.push_tasks(urls)
        
        # Start services
        await self.browser_service.start()
        await self.worker_service.start(num_workers)
        
        # Collect results
        results = self.redis.pop_all_results()
        
        # Process results
        for result in results:
            await self.url_registry.update_status(
                url_id=result.get('url_id'),
                success=result.get('success', False),
                job_count=len(result.get('jobs', []))
            )
        
        await self.worker_service.stop()
        await self.browser_service.stop()
        
        logger.info(f"✅ Scraping cycle complete: {len(results)} URLs processed")
    
    # ================================================================
    # Combined Cycle
    # ================================================================
    
    async def run_full_cycle(self, num_workers: int = 4):
        """
        Run a full cycle: discovery → scraping.
        """
        logger.info("🚀 Starting full cycle...")
        start_time = datetime.utcnow()
        
        # 1. Discovery
        if self.config.enable_discovery:
            discovery_results = await self.run_discovery_cycle()
            logger.info(f"🔍 Discovery: {discovery_results}")
        
        # 2. Scraping
        await self.run_scraping_cycle(num_workers)
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Full cycle complete in {elapsed:.2f}s")
    
    # ================================================================
    # Continuous Mode
    # ================================================================
    
    async def run_continuous(self):
        """
        Run the orchestrator continuously with schedule.
        This is the main entry point for production.
        """
        self.is_running = True
        await init_db()

        logger.info("🚀 Orchestrator running in continuous mode")
        logger.info(f"⏰ Cycle interval: {self.config.cycle_interval_hours} hours")
        
        while self.is_running:
            try:
                # Run a full cycle
                await self.run_full_cycle(
                    num_workers=self.config.workers_per_cycle
                )
                
                # Sleep until next cycle
                logger.info(
                    f"💤 Sleeping for {self.config.cycle_interval_hours} hours..."
                )
                await asyncio.sleep(self.config.cycle_interval_hours * 3600)
                
            except asyncio.CancelledError:
                logger.info("🛑 Orchestrator received cancellation signal")
                break
            except Exception as e:
                logger.error(f"❌ Cycle failed: {e}")
                # Wait 5 minutes before retrying on error
                logger.info("⏳ Waiting 5 minutes before retry...")
                await asyncio.sleep(300)
        
        await self.cleanup()
        logger.info("🛑 Orchestrator stopped")
    
    # ================================================================
    # Manual Trigger
    # ================================================================
    
    async def run_once(self, num_workers: int = 4):
        """
        Run a single cycle and exit.
        Useful for manual testing or cron jobs.
        """
        logger.info("🔁 Running one-time cycle...")
        await self.run_full_cycle(num_workers)
        await self.cleanup()
        logger.info("✅ One-time cycle complete")
    
    # ================================================================
    # Cleanup
    # ================================================================
    
    async def cleanup(self):
        """Clean up all resources."""
        logger.info("🧹 Cleaning up resources...")
        
        # Stop services if running
        if self.worker_service._is_running:
            await self.worker_service.stop()
        
        if self.browser_service.is_running():
            await self.browser_service.stop()
        
        # Close database connections
        await self.db.close()
        
        # Close Redis
        self.redis.close()
        
        logger.info("✅ Cleanup complete")
    
    def stop(self):
        """Request the orchestrator to stop."""
        self.is_running = False
        logger.info("🛑 Stop requested")
    
    # ================================================================
    # Stats
    # ================================================================
    
    async def get_stats(self) -> dict:
        """Get system statistics."""
        db_stats = await self.db.get_stats()
        url_stats = await self.url_registry.get_stats()
        query_stats = await self.query_registry.get_stats()
        
        return {
            **db_stats,
            'url_registry': url_stats,
            'query_registry': query_stats,
            'is_running': self.is_running,
            'config': {
                'workers_per_cycle': self.config.workers_per_cycle,
                'cycle_interval_hours': self.config.cycle_interval_hours,
                'max_urls_per_cycle': self.config.max_urls_per_cycle,
                'enable_discovery': self.config.enable_discovery,
            }
        }