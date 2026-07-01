# modules/aggregator.py
"""Aggregator - Combines and deduplicates scraped results."""

from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregates scraped results:
    1. Deduplicates by URL
    2. Normalizes company names
    3. Merges data from multiple sources
    4. Handles malformed results
    """
    
    # Common company name variations
    COMPANY_ALIASES = {
        'google inc': 'Google',
        'google llc': 'Google',
        'apple inc': 'Apple',
        'amazon inc': 'Amazon',
        'microsoft corp': 'Microsoft',
        'meta inc': 'Meta',
        'meta platforms': 'Meta',
        'tencent limited': 'Tencent',
        'alibaba group': 'Alibaba',
    }
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_ids = set()
    
    def aggregate(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Aggregate multiple scrape results into a single list of unique jobs.
        """
        all_jobs = []
        
        for result in results:
            if not result.get('success'):
                logger.warning(f"Skipping failed result: {result.get('url', 'unknown')}")
                continue
            
            jobs = result.get('jobs', [])
            if not jobs:
                continue
            
            all_jobs.extend(jobs)
        
        logger.info(f"📥 Aggregating {len(all_jobs)} raw jobs...")
        
        # Deduplicate
        deduplicated = self.deduplicate(all_jobs)
        
        # Normalize
        normalized = self.normalize_batch(deduplicated)
        
        logger.info(f"✅ Aggregated {len(normalized)} unique jobs")
        return normalized
    
    def deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """
        Remove duplicate jobs by URL.
        Also handles jobs from the same company with same title.
        """
        seen_urls = set()
        seen_title_company = set()
        unique_jobs = []
        
        for job in jobs:
            url = job.get('url', '')
            
            # Deduplicate by URL
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            
            # Deduplicate by (title, company) combination
            title = job.get('title', '').lower().strip()
            company = job.get('company', '').lower().strip()
            key = f"{title}|{company}"
            
            if key in seen_title_company:
                continue
            seen_title_company.add(key)
            
            unique_jobs.append(job)
        
        logger.info(f"🔍 Deduplicated: {len(jobs)} → {len(unique_jobs)}")
        return unique_jobs
    
    def normalize_batch(self, jobs: List[Dict]) -> List[Dict]:
        """Normalize a batch of jobs."""
        normalized = []
        
        for job in jobs:
            normalized_job = self.normalize(job)
            if normalized_job:
                normalized.append(normalized_job)
        
        return normalized
    
    def normalize(self, job: Dict) -> Optional[Dict]:
        """
        Normalize a single job:
        - Clean company name
        - Clean title
        - Ensure required fields
        - Generate consistent ID
        """
        # Ensure required fields
        if not job.get('title') or not job.get('url'):
            return None
        
        # Clean title
        job['title'] = self._clean_title(job['title'])
        
        # Normalize company
        job['company'] = self._normalize_company(job.get('company', ''))
        
        # Generate stable ID if not present
        if not job.get('job_id'):
            job['job_id'] = self._generate_id(job)
        
        # Remove any None values from the job
        job = {k: v for k, v in job.items() if v is not None}
        
        return job
    
    def _clean_title(self, title: str) -> str:
        """Clean up job title."""
        if not title:
            return ''
        
        # Remove extra whitespace
        cleaned = ' '.join(title.split())
        
        # Remove common prefixes
        prefixes_to_remove = ['(Remote)', '(Hybrid)', '[Remote]', '[Hybrid]']
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned
    
    def _normalize_company(self, company: str) -> str:
        """Normalize company name."""
        if not company:
            return 'Unknown'
        
        company_lower = company.lower().strip()
        
        # Check aliases
        if company_lower in self.COMPANY_ALIASES:
            return self.COMPANY_ALIASES[company_lower]
        
        # Capitalize properly
        words = company.split()
        normalized = ' '.join([word.capitalize() for word in words])
        
        return normalized
    
    def _generate_id(self, job: Dict) -> str:
        """Generate a stable ID for a job."""
        url = job.get('url', '')
        if url:
            return hashlib.md5(url.encode()).hexdigest()
        
        # Fallback: hash company + title
        company = job.get('company', '')
        title = job.get('title', '')
        return hashlib.md5(f"{company}|{title}".encode()).hexdigest()