# services/worker.py
"""Worker Service - Manages task loop, NOT scraping logic."""

import asyncio
from typing import List, Dict, Optional
import logging

from modules.worker import Worker
from services.browser import BrowserService
from components.redis_component import RedisComponent
from modules.config import Config

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages workers and the task loop.
    Does NOT contain scraping logic - that's in Worker.
    """
    
    def __init__(self, 
                 config: Config,
                 browser_service: BrowserService,
                 redis_component: RedisComponent):
        self.config = config
        self.browser_service = browser_service
        self.redis = redis_component
        
        self.workers: List[Worker] = []
        self._is_running = False
        self._stop_requested = False
        self._task_counter = 0
        self._success_count = 0
        self._failure_count = 0
        self._current_worker_index = 0
    
    async def start(self, num_workers: int = 4):
        """Start the worker service."""
        if self._is_running:
            return
        
        if not self.browser_service.is_running():
            raise RuntimeError("Browser service must be started first")
        
        logger.info(f"🟢 Starting Worker Service with {num_workers} workers...")
        
        # Create workers (just IDs, no context yet)
        self.workers = [Worker(i) for i in range(num_workers)]
        self._is_running = True
        self._stop_requested = False
        self._current_worker_index = 0
        
        # Start the main task loop
        await self._task_loop()
    
    async def _task_loop(self):
        """Main loop: pull tasks, assign to workers, collect results."""
        logger.info("🔄 Task loop started")
        
        while not self._stop_requested:
            try:
                # 1. Get a task from Redis
                task = self.redis.pop_task(timeout=5)
                
                if task is None:
                    await asyncio.sleep(1)
                    continue
                
                # 2. Get next available worker
                worker = self._get_next_worker()
                if worker is None:
                    await asyncio.sleep(1)
                    self.redis.push_task(task)  # Re-queue
                    continue
                
                # 3. Get a context from BrowserService
                context = await self.browser_service.get_context(worker.worker_id)
                
                # 4. Assign task to worker (worker does ALL scraping)
                self._task_counter += 1
                result = await worker.scrape(
                    url=task.get("url"),
                    url_id=task.get("url_id"),
                    company=task.get("company", "Unknown"),
                    context=context
                )
                
                # 5. Handle result
                await self._handle_result(result)
                
            except Exception as e:
                logger.error(f"Task loop error: {e}")
                await asyncio.sleep(2)
        
        logger.info("🛑 Task loop stopped")
    
    def _get_next_worker(self) -> Optional[Worker]:
        """Get the next worker (round-robin)."""
        if not self.workers:
            return None
        
        worker = self.workers[self._current_worker_index]
        self._current_worker_index = (self._current_worker_index + 1) % len(self.workers)
        return worker
    
    async def _handle_result(self, result):
        """Push result to Redis."""
        if result.success:
            self._success_count += 1
            self.redis.push_result({
                "url_id": result.url_id,
                "url": result.url,
                "company": result.company,
                "success": True,
                "jobs": result.jobs,
                "elapsed": result.elapsed,
                "timestamp": result.timestamp
            })
            logger.info(f"✅ Scraped {len(result.jobs)} jobs from {result.url}")
        else:
            self._failure_count += 1
            self.redis.push_failure({
                "url_id": result.url_id,
                "url": result.url,
                "company": result.company,
                "success": False,
                "error": result.error,
                "elapsed": result.elapsed,
                "timestamp": result.timestamp
            })
            logger.warning(f"❌ Failed to scrape {result.url}: {result.error}")
    
    async def stop(self):
        """Stop the worker service."""
        if not self._is_running:
            return
        
        logger.info("🛑 Stopping Worker Service...")
        self._stop_requested = True
        self._is_running = False
        
        await asyncio.sleep(2)
        logger.info("✅ Worker Service stopped")
    
    def get_stats(self) -> Dict:
        """Get worker service statistics."""
        return {
            "is_running": self._is_running,
            "total_workers": len(self.workers),
            "tasks_completed": self._task_counter,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self._success_count / max(self._task_counter, 1)
        }