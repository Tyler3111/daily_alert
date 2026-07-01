# data_sources/discovery_engine.py
"""Discovery Engine - LLM query generation + search orchestration."""

import json
import logging
import subprocess
from typing import List, Dict, Optional

import aiohttp

from core.config import Config
from data_sources.url_registry import URLRegistry
from data_sources.query_registry import QueryRegistry
from scraper.search_executor import SearchExecutor

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """
    Complete discovery engine that:
    1. Uses LLM to generate search queries
    2. Executes searches via Google
    3. Extracts and registers career page URLs
    """
    
    def __init__(self, config: Config, url_registry: URLRegistry, query_registry: QueryRegistry):
        self.config = config
        self.url_registry = url_registry
        self.query_registry = query_registry
        self.search_executor = SearchExecutor()
        
        # LLM backend detection
        self.backend = self._detect_backend()
        self.api_key = config.llm_api_key
        self.model = config.llm_model
        
        # Cache for already generated queries to avoid duplicates
        self._generated_queries = set()
    
    # ================================================================
    # LLM Backend Detection
    # ================================================================
    
    def _detect_backend(self) -> str:
        """Detect which LLM backend to use."""
        if self.config.llm_api_key:
            return "openrouter"
        
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return "ollama"
        except:
            pass
        
        return "fallback"
    
    # ================================================================
    # Query Generation (LLM)
    # ================================================================
    
    async def generate_search_queries(
        self,
        existing_queries: List[str],
        location: str = "Hong Kong",
        keywords: List[str] = None,
        num_queries: int = 10
    ) -> List[str]:
        """
        Generate search queries using LLM.
        Takes existing queries as context to avoid duplicates.
        """
        if not existing_queries:
            return await self._generate_initial_queries(location, keywords)
        
        context = self._build_query_context(existing_queries)
        
        prompt = f"""
        You are a job search expert. Generate {num_queries} Google search queries to find tech jobs in {location}.
        
        {context}
        
        Requirements:
        1. Generate queries DIFFERENT from what's been tried
        2. Use keywords: {keywords or ['software', 'engineer', 'developer']}
        3. Include location: {location}, Hong Kong, HK
        4. Use Google search operators
        5. Be specific and varied
        
        Return as a JSON array of strings. Only the JSON array, no other text.
        """
        
        return await self._call_llm(prompt)
    
    async def _generate_initial_queries(self, location: str, keywords: List[str] = None) -> List[str]:
        """Generate initial set of diverse queries."""
        keywords = keywords or ["software", "engineer", "developer"]
        
        prompt = f"""
        Generate 20 diverse Google search queries to find tech jobs in {location}.
        
        Include these types:
        1. Company-specific: site:company.com/careers
        2. Title-specific: "software engineer" Hong Kong
        3. Industry-specific: fintech jobs Hong Kong
        4. Role-specific: backend engineer Hong Kong
        5. Generic: tech jobs Hong Kong
        6. Hiring signals: "hiring" Hong Kong developer
        7. Career page: intitle:"careers" Hong Kong
        
        Return as JSON array of strings.
        """
        
        return await self._call_llm(prompt)
    
    def _build_query_context(self, existing_queries: List[str]) -> str:
        """Build context from existing queries."""
        if not existing_queries:
            return ""
        
        context = "Already tried queries:\n"
        for q in existing_queries[:15]:
            context += f"- {q}\n"
        
        return context
    
    # ================================================================
    # LLM API Calls
    # ================================================================
    
    async def _call_llm(self, prompt: str) -> List[str]:
        """Call the configured LLM backend."""
        if self.backend == "openrouter":
            return await self._call_openrouter(prompt)
        elif self.backend == "ollama":
            return await self._call_ollama(prompt)
        else:
            return self._get_fallback_queries()
    
    async def _call_openrouter(self, prompt: str) -> List[str]:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 800,
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        return self._parse_response(content)
                    else:
                        logger.error(f"OpenRouter error: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"OpenRouter call failed: {e}")
                return []
    
    async def _call_ollama(self, prompt: str) -> List[str]:
        """Call local Ollama API."""
        payload = {
            "model": "llama2:7b",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.8
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=120
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("response", "")
                        return self._parse_response(content)
                    else:
                        logger.error(f"Ollama error: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Ollama call failed: {e}")
                return []
    
    def _parse_response(self, content: str) -> List[str]:
        """Parse LLM response to extract JSON array."""
        import re
        
        # Try to find JSON array
        json_pattern = r'\[[^\]]*\]'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                result = json.loads(match)
                if isinstance(result, list):
                    # Filter out empty or too-short queries
                    return [q for q in result if len(q) > 3]
            except:
                continue
        
        # Fallback: split by newlines
        lines = [line.strip().strip('"') for line in content.split('\n') if line.strip()]
        queries = [l for l in lines if len(l) > 5 and not l.startswith('{') and not l.startswith('[')]
        return queries[:15]
    
    def _get_fallback_queries(self) -> List[str]:
        """Fallback queries when LLM is unavailable."""
        return [
            'site:google.com/careers software engineer Hong Kong',
            'site:microsoft.com/careers software engineer Hong Kong',
            'site:apple.com/careers software engineer Hong Kong',
            '"software engineer" Hong Kong jobs',
            '"backend developer" Hong Kong',
            '"full stack engineer" Hong Kong',
            'tech jobs Hong Kong software engineer',
            'fintech jobs Hong Kong developer',
            'startup jobs Hong Kong engineer',
            'intitle:"careers" "Hong Kong" software engineer',
            'inurl:jobs "Hong Kong" developer',
            '"join our team" Hong Kong engineer',
            'banking tech jobs Hong Kong',
            'crypto jobs Hong Kong developer',
            '"Hong Kong" "software engineer" hiring'
        ]
    
    # ================================================================
    # Complete Discovery Cycle
    # ================================================================
    
    async def run_discovery_cycle(self) -> Dict:
        """
        Run a complete discovery cycle:
        1. Get existing queries (untried only)
        2. LLM generates new queries
        3. Execute searches
        4. Add found URLs to registry
        """
        logger.info("🔍 Starting discovery cycle...")
        
        # 1. Get existing queries (only untried ones for context)
        untried = await self.query_registry.get_untried_queries(limit=50)
        existing_texts = [q['query'] for q in untried]
        
        # 2. Generate new queries with LLM
        new_queries = await self.generate_search_queries(
            existing_queries=existing_texts,
            location=self.config.default_location,
            keywords=self.config.search_keywords,
            num_queries=15
        )
        
        # 3. Add queries to registry
        added_count = 0
        for query in new_queries:
            # Skip duplicates
            if query in self._generated_queries:
                continue
            self._generated_queries.add(query)
            
            # Add to registry
            query_id = await self.query_registry.add_query(query)
            if query_id:
                added_count += 1
        
        logger.info(f"📝 Added {added_count} new queries")
        
        # 4. Execute searches for untried queries
        untried = await self.query_registry.get_untried_queries(limit=20)
        
        total_urls_found = 0
        executed_count = 0
        
        for query_data in untried:
            query = query_data['query']
            query_id = query_data['id']
            
            # Execute search
            try:
                search_results = await self.search_executor.execute_query(query, num_results=8)
                executed_count += 1
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
                await self.query_registry.update_status(query_id, success=False)
                continue
            
            # Add URLs to registry
            urls_found = 0
            for result in search_results:
                if result.get('url'):
                    company = result.get('company', 'unknown')
                    await self.url_registry.add_url(
                        url=result['url'],
                        source=company.lower().replace(" ", "_"),
                        company=company,
                        metadata={'discovery_query': query}
                    )
                    urls_found += 1
                    total_urls_found += 1
            
            # Update query status
            await self.query_registry.update_status(
                query_id=query_id,
                success=urls_found > 0,
                urls_found=urls_found
            )
            
            logger.info(f"🔍 '{query[:40]}...' found {urls_found} URLs")
        
        logger.info(f"✅ Discovery complete: {total_urls_found} new URLs from {executed_count} queries")
        
        return {
            'queries_generated': added_count,
            'queries_executed': executed_count,
            'urls_found': total_urls_found
        }