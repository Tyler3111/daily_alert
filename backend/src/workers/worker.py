import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from constants.string_constants import JOB_SELECTORS, SCRAPER_CONFIG
from modules.vetting_engine import VettingEngine
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result from a single scrape job."""
    url_id: str
    url: str
    company: str
    success: bool
    jobs: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    elapsed: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Worker:
    """
    Pure scraper worker.
    All scraping logic lives here.
    """
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.vetting_engine = VettingEngine()
    
    async def scrape(self, url: str, url_id: str, company: str, context: BrowserContext) -> ScrapeResult:
        """
        Execute a single scrape job.
        This is the entry point called by WorkerService.
        """
        start_time = time.time()
        page = await context.new_page()
        
        try:
            # All scraping logic is in _scrape_url
            jobs = await self._scrape_url(page, url, company)
            
            elapsed = time.time() - start_time
            
            return ScrapeResult(
                url_id=url_id,
                url=url,
                company=company,
                success=True,
                jobs=jobs,
                elapsed=elapsed
            )
            
        except Exception as e:
            elapsed = time.time() - start_time
            return ScrapeResult(
                url_id=url_id,
                url=url,
                company=company,
                success=False,
                error=str(e),
                elapsed=elapsed
            )
        finally:
            await page.close()
    
    async def _scrape_url(self, page: Page, url: str, company: str) -> List[Dict]:
        await self._navigate(page, url)
        await self._wait_for_jobs(page)
        raw_jobs = await self._extract_jobs(page, url, company)
        vetted_jobs = self.vetting_engine.vet_jobs(raw_jobs)
        return vetted_jobs
    
    async def _navigate(self, page: Page, url: str):
        try:
            await page.goto(url, wait_until="networkidle", timeout=SCRAPER_CONFIG['navigation_timeout'])
        except PlaywrightTimeout:
            await page.goto(url, wait_until="domcontentloaded", timeout=SCRAPER_CONFIG['navigation_timeout'])
    
    async def _wait_for_jobs(self, page: Page):
        try:
            await page.wait_for_selector(
                ", ".join(JOB_SELECTORS),
                timeout=SCRAPER_CONFIG['wait_timeout'],
                state="attached"
            )
        except PlaywrightTimeout:
            # Fallback: wait for any link that might be a job
            try:
                await page.wait_for_selector(
                    'a[href*="job"], a[href*="career"], a[href*="position"]',
                    timeout=5000
                )
            except PlaywrightTimeout:
                # No jobs found, but continue (might be no jobs on page)
                pass
    
    async def _extract_jobs(self, page: Page, base_url: str, company: str) -> List[Dict]:
        """Extract job listings from the page using JavaScript."""
        raw_jobs = await page.evaluate(self._get_extraction_script())
        
        # Add metadata to each job
        for job in raw_jobs:
            job['company'] = company
            job['source_url'] = base_url
        
        return raw_jobs
    
    def _get_extraction_script(self) -> str:
        """Return JavaScript to extract jobs from the page."""
        return f'''
            () => {{
                const results = [];
                const seen = new Set();
                const selectors = {JOB_SELECTORS};
                
                const elements = document.querySelectorAll(selectors.join(','));
                
                for (const el of elements) {{
                    let href = el.href || el.getAttribute('href');
                    if (!href) continue;
                    
                    if (href.startsWith('/')) {{
                        href = window.location.origin + href;
                    }}
                    
                    const title = el.textContent.trim();
                    if (!title || title.length < 3) continue;
                    
                    const parent = el.closest('div, li, tr, article');
                    const context = parent ? parent.textContent.trim() : '';
                    
                    const key = href + title;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    
                    results.push({{
                        title: title,
                        url: href,
                        context: context.substring(0, 500)
                    }});
                }}
                
                return results;
            }}