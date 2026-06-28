# modules/browser_pool.py
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext
from modules.config import Config
from modules.context_manager import ContextManager
import logging
logger = logging.getLogger(__name__)

class BrowserPool:
    
    def __init__(self, config: Config):
        self.config = config
        self._browser: Optional[Browser] = None
        self._context_manager: Optional[ContextManager] = None
        self._is_running = False
        self._playwright = None

    
    async def start(self):
        if self._is_running:
            return
        
        logger.info("🚀 Launching browser...")
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer"
            ]
        )
        
        self._context_manager = ContextManager(
            browser=self._browser,
            data_dir="./worker_data"
        )
        
        self._is_running = True
        logger.info("✅ Browser launched")
    
    async def get_context(self, worker_id: int) -> BrowserContext:
        """Get an isolated context for a worker."""
        if not self._is_running:
            raise RuntimeError("Browser pool not started. Call start() first.")
        return await self._context_manager.create_context(worker_id)
    
    async def save_context_state(self, worker_id: int):
        """Save a worker's context state (cookies, cache)."""
        if self._context_manager:
            await self._context_manager.save_context_state(worker_id)
    
    async def stop(self):
        """Close the browser and cleanup."""
        if not self._is_running:
            return
        
        logger.info("🛑 Closing browser...")
        
        if self._context_manager:
            await self._context_manager.close_all()
        
        if self._browser:
            await self._browser.close()
        
        if self._playwright:
            await self._playwright.stop()
        
        self._is_running = False
        logger.info("✅ Browser closed")
    
    def is_running(self) -> bool:
        return self._is_running
    
    def get_browser(self) -> Optional[Browser]:
        """Get the underlying browser instance (for advanced use)."""
        return self._browser