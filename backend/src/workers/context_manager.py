# modules/context_manager.py
"""Manages isolated browser contexts for workers."""

import json
import os
from typing import Dict, Optional
from playwright.async_api import Browser, BrowserContext
import logging

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages isolated browser contexts for each worker.
    Each worker gets its own cookies, cache, and storage.
    """
    
    def __init__(self, browser: Browser, data_dir: str = "./worker_data"):
        self.browser = browser
        self.data_dir = data_dir
        self.contexts: Dict[int, BrowserContext] = {}
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
    
    async def create_context(self, worker_id: int) -> BrowserContext:
        """
        Create or load an isolated context for a worker.
        Each worker gets its own cookies, cache, and storage.
        """
        state_file = os.path.join(self.data_dir, f"worker_{worker_id}_state.json")
        
        # Try to load existing state
        storage_state = None
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    storage_state = json.load(f)
                logger.info(f"📂 Worker {worker_id}: loaded state from {state_file}")
            except Exception as e:
                logger.warning(f"Failed to load state for worker {worker_id}: {e}")
        
        # Create context with or without saved state
        if storage_state:
            context = await self.browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1280, "height": 720},
                user_agent=self._get_user_agent(),
                locale="en-US",
                timezone_id="Asia/Hong_Kong"
            )
        else:
            context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=self._get_user_agent(),
                locale="en-US",
                timezone_id="Asia/Hong_Kong"
            )
        
        self.contexts[worker_id] = context
        logger.info(f"🟢 Worker {worker_id}: context created")
        return context
    
    async def save_context_state(self, worker_id: int):
        """Save the context state (cookies, localStorage, etc.) for a worker."""
        if worker_id not in self.contexts:
            return
        
        try:
            state = await self.contexts[worker_id].storage_state()
            state_file = os.path.join(self.data_dir, f"worker_{worker_id}_state.json")
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"💾 Worker {worker_id}: state saved to {state_file}")
        except Exception as e:
            logger.error(f"Failed to save state for worker {worker_id}: {e}")
    
    async def close_context(self, worker_id: int):
        """Close a worker's context and save its state."""
        if worker_id in self.contexts:
            await self.save_context_state(worker_id)
            await self.contexts[worker_id].close()
            del self.contexts[worker_id]
            logger.info(f"🛑 Worker {worker_id}: context closed")
    
    async def close_all(self):
        """Close all contexts and save their states."""
        for worker_id in list(self.contexts.keys()):
            await self.close_context(worker_id)
    
    def _get_user_agent(self) -> str:
        """Get a realistic user agent."""
        import random
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        return random.choice(user_agents)