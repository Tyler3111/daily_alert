# scraper/worker.py
"""Worker - Smart scraper that discovers and scrapes via Google searches."""

import time
import asyncio
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from core.string_constants import JOB_SELECTORS, SCRAPER_CONFIG
from scraper.vetting_engine import VettingEngine
from scraper.models import ScrapeResult, SearchResult
import logging

logger = logging.getLogger(__name__)


class Worker:
    """
    Smart worker that discovers job listings via Google searches.
    No static URL lists — everything comes from search queries.
    """
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.vetting_engine = VettingEngine()
        
        # Cache to avoid re-searching same queries
        self._query_cache = {}
    
    # ================================================================
    # Main Entry Point
    # ================================================================
    
    async def execute_search(
        self,
        context: BrowserContext,
        query: str,
        query_id: str,
        num_results: int = 10
    ) -> SearchResult:
        """
        Execute a Google search to discover career pages.
        This is the primary entry point for discovery tasks.
        """
        start_time = time.time()
        page = await context.new_page()
        
        try:
            # 1. Perform Google search
            discovered_urls = await self._search_google(page, query, num_results)
            
            # 2. Filter for career pages
            career_urls = self._filter_career_urls(discovered_urls, query)
            
            # 3. Optionally, scrape the first few career pages found
            jobs = []
            for url_data in career_urls[:5]:
                try:
                    scraped = await self._scrape_url(
                        page=page,
                        url=url_data['url'],
                        company=url_data['company']
                    )
                    jobs.extend(scraped)
                except Exception as e:
                    logger.warning(f"Failed to scrape {url_data['url']}: {e}")
            
            elapsed = time.time() - start_time
            
            return SearchResult(
                query_id=query_id,
                query=query,
                success=True,
                discovered_urls=career_urls,
                jobs=jobs,
                elapsed=elapsed
            )
            
        except Exception as e:
            elapsed = time.time() - start_time
            return SearchResult(
                query_id=query_id,
                query=query,
                success=False,
                error=str(e),
                elapsed=elapsed
            )
        finally:
            await page.close()
    
    # ================================================================
    # Google Search
    # ================================================================
    
    async def _search_google(self, page: Page, query: str, num_results: int) -> List[Dict]:
        """
        Perform a Google search and extract URLs with context.
        """
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
        
        logger.info(f"🔍 Searching: {query}")
        
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        
        # Extract URLs from search results
        urls = await page.evaluate('''
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="http"]');
                for (const link of links) {
                    const href = link.href;
                    // Skip Google's own links
                    if (href.startsWith('https://www.google.com/')) continue;
                    if (href.startsWith('https://accounts.google.com/')) continue;
                    if (href.startsWith('https://webcache.googleusercontent.com/')) continue;
                    
                    // Get surrounding text for context
                    const parent = link.closest('div, li, section, article');
                    const context = parent ? parent.textContent.trim() : '';
                    
                    results.push({
                        url: href,
                        title: link.textContent.trim(),
                        context: context.substring(0, 500)
                    });
                }
                return results;
            }
        ''')
        
        logger.info(f"📊 Found {len(urls)} URLs from search")
        return urls
    
    def _filter_career_urls(self, urls: List[Dict], query: str) -> List[Dict]:
        """
        Filter URLs to only include career pages.
        Uses soft matching with career-related keywords.
        """
        career_keywords = [
            'career', 'careers', 'jobs', 'join', 'work', 'hire', 'hiring',
            'recruit', 'recruiting', 'opportunities', 'positions', 
            'employment', 'talent', 'team', 'about', 'culture',
            'benefits', 'perks', 'life', 'people', 'talent'
        ]
        
        # Common job board URLs to skip
        skip_domains = [
            'linkedin.com', 'indeed.com', 'glassdoor.com', 
            'monster.com', 'ziprecruiter.com', 'careerbuilder.com',
            'simplyhired.com', 'dice.com', 'stackoverflow.com'
        ]
        
        filtered = []
        seen_urls = set()
        
        for url_data in urls:
            url = url_data.get('url', '')
            if not url:
                continue
            
            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Skip job boards
            if any(domain in url.lower() for domain in skip_domains):
                continue
            
            url_lower = url.lower()
            title = url_data.get('title', '').lower()
            context = url_data.get('context', '').lower()
            
            # Check if URL or context contains career keywords
            text_to_check = f"{url_lower} {title} {context}"
            
            # Count how many career keywords match
            match_count = sum(1 for kw in career_keywords if kw in text_to_check)
            
            # If at least 2 keywords match, it's likely a career page
            if match_count >= 2:
                company = self._extract_company_from_url(url)
                filtered.append({
                    'url': url,
                    'company': company,
                    'title': url_data.get('title', ''),
                    'context': url_data.get('context', '')[:200],
                    'match_score': match_count,
                    'discovery_query': query
                })
        
        # Sort by match score (highest first)
        filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        logger.info(f"🎯 Found {len(filtered)} career pages from {len(urls)} results")
        return filtered
    
    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from a URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove www. and subdomains
        parts = domain.split('.')
        if len(parts) >= 2:
            # Try to extract company name
            if parts[0] in ['www', 'careers', 'jobs'] and len(parts) >= 3:
                return parts[1].capitalize()
            return parts[0].capitalize()
        return domain
    
    # ================================================================
    # URL Scraping (Same as before)
    # ================================================================
    
    async def _scrape_url(self, page: Page, url: str, company: str) -> List[Dict]:
        """
        Scrape a single URL for job listings.
        """
        await self._navigate(page, url)
        await self._wait_for_jobs(page)
        raw_jobs = await self._extract_jobs(page, url, company)
        return self.vetting_engine.vet_jobs(raw_jobs)
    
    async def _navigate(self, page: Page, url: str):
        """Navigate to URL with timeout handling."""
        try:
            await page.goto(url, wait_until="networkidle", timeout=SCRAPER_CONFIG['navigation_timeout'])
        except PlaywrightTimeout:
            await page.goto(url, wait_until="domcontentloaded", timeout=SCRAPER_CONFIG['navigation_timeout'])
    
    async def _wait_for_jobs(self, page: Page):
        """Wait for job listings to appear."""
        try:
            await page.wait_for_selector(
                ", ".join(JOB_SELECTORS),
                timeout=SCRAPER_CONFIG['wait_timeout'],
                state="attached"
            )
        except PlaywrightTimeout:
            try:
                await page.wait_for_selector(
                    'a[href*="job"], a[href*="career"], a[href*="position"]',
                    timeout=5000
                )
            except PlaywrightTimeout:
                pass
    
    async def _extract_jobs(self, page: Page, base_url: str, company: str) -> List[Dict]:
        """Extract job listings from the page using JavaScript."""
        raw_jobs = await page.evaluate(self._get_extraction_script())
        
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
        '''