# scraper/search_executor.py
"""Search Executor - Executes Google searches and extracts career page URLs."""

import asyncio
import re
import time
from typing import List, Dict, Optional, Set
from urllib.parse import quote_plus, urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import logging

logger = logging.getLogger(__name__)


class SearchExecutor:
    """
    Executes Google search queries and extracts career page URLs.
    Handles pagination, filtering, and rate limiting.
    """
    
    # Common career page URL patterns to look for
    CAREER_URL_PATTERNS = [
        r'/careers?',
        r'/jobs',
        r'/join-us',
        r'/career',
        r'/job-openings',
        r'/positions',
        r'/employment',
        r'/about/careers',
        r'/career-opportunities',
        r'/job-listings',
        r'/work-with-us',
        r'/recruiting',
        r'/talent',
        r'/people',
        r'/life',
        r'/culture',
        r'/team',
    ]
    
    # Keywords that indicate a career page
    CAREER_KEYWORDS = [
        'career', 'careers', 'jobs', 'join', 'work', 'hire', 'hiring',
        'recruit', 'recruiting', 'opportunities', 'positions',
        'employment', 'talent', 'team', 'about', 'culture',
        'benefits', 'perks', 'people', 'life', 'talent',
    ]
    
    # Domains to skip (job boards, aggregators)
    SKIP_DOMAINS = [
        'linkedin.com', 'indeed.com', 'glassdoor.com',
        'monster.com', 'ziprecruiter.com', 'careerbuilder.com',
        'simplyhired.com', 'dice.com', 'stackoverflow.com',
        'google.com', 'youtube.com', 'facebook.com', 'twitter.com',
        'instagram.com', 'reddit.com', 'wikipedia.org',
    ]
    
    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize the search executor.
        
        Args:
            rate_limit_delay: Seconds to wait between searches to avoid rate limiting
        """
        self.rate_limit_delay = rate_limit_delay
        self._last_search_time = 0
    
    # ================================================================
    # Main Execution
    # ================================================================
    
    async def execute_query(
        self,
        query: str,
        num_results: int = 10,
        max_pages: int = 2,
        headless: bool = True
    ) -> List[Dict]:
        """
        Execute a Google search query and extract career page URLs.
        
        Args:
            query: The search query string
            num_results: Number of results to return
            max_pages: Maximum number of search result pages to check
            headless: Whether to run browser in headless mode
        
        Returns:
            List of dicts with url, company, title, context
        """
        # Rate limiting
        await self._apply_rate_limit()
        
        logger.info(f"🔍 Executing search: {query[:60]}...")
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            
            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent=self._get_user_agent(),
                    locale="en-US",
                    timezone_id="Asia/Hong_Kong"
                )
                
                page = await context.new_page()
                
                # Search across pages
                for page_num in range(max_pages):
                    start = page_num * 10
                    search_url = self._build_search_url(query, start)
                    
                    try:
                        page_results = await self._search_page(page, search_url, query)
                        results.extend(page_results)
                        
                        # Break if we have enough results
                        if len(results) >= num_results:
                            break
                        
                        # Check if there's a next page
                        if page_num < max_pages - 1:
                            next_exists = await self._has_next_page(page)
                            if not next_exists:
                                break
                            
                    except Exception as e:
                        logger.warning(f"Page {page_num + 1} search failed: {e}")
                        break
                
                await browser.close()
                
            except Exception as e:
                logger.error(f"Search execution failed: {e}")
                await browser.close()
                return []
        
        # Filter and clean results
        filtered = self._filter_career_urls(results, query)
        
        logger.info(f"✅ Found {len(filtered)} career pages from '{query[:40]}...'")
        return filtered
    
    async def _search_page(self, page, search_url: str, query: str) -> List[Dict]:
        """Search a single page and extract results."""
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        
        # Wait for results to load
        try:
            await page.wait_for_selector('#search, #rso', timeout=5000)
        except PlaywrightTimeout:
            pass
        
        # Extract URLs
        urls = await page.evaluate(self._get_extraction_script())
        
        return urls
    
    def _build_search_url(self, query: str, start: int = 0) -> str:
        """Build a Google search URL."""
        return f"https://www.google.com/search?q={quote_plus(query)}&num=10&start={start}"
    
    async def _has_next_page(self, page) -> bool:
        """Check if there's a next page of results."""
        try:
            next_button = await page.query_selector('a#pnnext, a[aria-label="Next"]')
            return next_button is not None
        except:
            return False
    
    # ================================================================
    # URL Extraction Script
    # ================================================================
    
    def _get_extraction_script(self) -> str:
        """Return JavaScript to extract URLs from search results."""
        return '''
            () => {
                const results = [];
                const seen = new Set();
                
                // Find all result containers
                const containers = document.querySelectorAll('div.g, div.tF2Cxc, div[data-sokoban-container]');
                
                for (const container of containers) {
                    // Find the link
                    const link = container.querySelector('a[href*="http"]');
                    if (!link) continue;
                    
                    const href = link.href;
                    
                    // Skip Google's own links
                    if (href.startsWith('https://www.google.com/')) continue;
                    if (href.startsWith('https://accounts.google.com/')) continue;
                    if (href.startsWith('https://webcache.googleusercontent.com/')) continue;
                    if (href.includes('googleadservices')) continue;
                    
                    // Get title
                    const titleEl = container.querySelector('h3, [role="heading"]');
                    const title = titleEl ? titleEl.textContent.trim() : link.textContent.trim();
                    
                    // Get description/snippet
                    const descEl = container.querySelector('div[data-sncf], div.VwiC3b, div.IsZvec');
                    const description = descEl ? descEl.textContent.trim() : '';
                    
                    // Get display URL
                    const displayUrlEl = container.querySelector('div.TbwUpd, cite, span[role="text"]');
                    const displayUrl = displayUrlEl ? displayUrlEl.textContent.trim() : '';
                    
                    const key = href + title;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    
                    results.push({
                        url: href,
                        title: title || '',
                        description: description.substring(0, 500),
                        display_url: displayUrl || '',
                        container_text: container.textContent.trim().substring(0, 300)
                    });
                }
                
                return results;
            }
        '''
    
    # ================================================================
    # Filtering
    # ================================================================
    
    def _filter_career_urls(self, urls: List[Dict], query: str) -> List[Dict]:
        """
        Filter URLs to only include career pages.
        Uses soft matching with career-related keywords.
        """
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
            
            # Skip invalid domains
            if self._should_skip_domain(url):
                continue
            
            # Calculate career match score
            score = self._calculate_career_score(url_data)
            
            # Only keep if score is high enough
            if score >= 2:
                company = self._extract_company_from_url(url)
                filtered.append({
                    'url': url,
                    'company': company,
                    'title': url_data.get('title', ''),
                    'description': url_data.get('description', ''),
                    'display_url': url_data.get('display_url', ''),
                    'match_score': score,
                    'discovery_query': query,
                })
        
        # Sort by match score (highest first)
        filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return filtered
    
    def _calculate_career_score(self, url_data: Dict) -> int:
        """
        Calculate a score indicating how likely this is a career page.
        Higher score = more likely to be a career page.
        """
        score = 0
        
        url = url_data.get('url', '').lower()
        title = url_data.get('title', '').lower()
        description = url_data.get('description', '').lower()
        text_to_check = f"{url} {title} {description}"
        
        # Check URL patterns
        for pattern in self.CAREER_URL_PATTERNS:
            if re.search(pattern, url):
                score += 2
                break
        
        # Check for career keywords in title/description
        for keyword in self.CAREER_KEYWORDS:
            if keyword in text_to_check:
                score += 1
                break
        
        # Bonus: check for company-like URLs
        parsed = urlparse(url)
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) >= 2 and domain_parts[0] not in ['www', 'careers', 'jobs']:
            # Looks like a company domain
            score += 1
        
        # Penalty: check for job board indicators
        job_board_indicators = ['jobs.com', 'careers.com', 'indeed', 'glassdoor', 'linkedin']
        for indicator in job_board_indicators:
            if indicator in url:
                score -= 2
                break
        
        return max(0, score)
    
    def _should_skip_domain(self, url: str) -> bool:
        """Check if the URL's domain should be skipped."""
        for domain in self.SKIP_DOMAINS:
            if domain in url.lower():
                return True
        return False
    
    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from a URL."""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove subdomains
        parts = domain.split('.')
        if len(parts) >= 2:
            # Handle common subdomains
            if parts[0] in ['www', 'careers', 'jobs', 'apply'] and len(parts) >= 3:
                return parts[1].capitalize()
            
            # Try to get the main domain name
            main_part = parts[0]
            if main_part in ['www', 'careers', 'jobs', 'apply']:
                return parts[1].capitalize() if len(parts) >= 3 else domain
            return main_part.capitalize()
        
        return domain
    
    # ================================================================
    # Rate Limiting
    # ================================================================
    
    async def _apply_rate_limit(self):
        """Apply rate limiting to avoid Google blocking."""
        current_time = time.time()
        time_since_last = current_time - self._last_search_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self._last_search_time = time.time()
    
    def _get_user_agent(self) -> str:
        """Get a realistic user agent."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        import random
        return random.choice(user_agents)
    
    # ================================================================
    # Utility Methods
    # ================================================================
    
    async def check_url_validity(self, url: str) -> bool:
        """
        Check if a URL is accessible and valid.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                response = await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                is_valid = response is not None and response.status < 400
                await browser.close()
                return is_valid
            except:
                await browser.close()
                return False