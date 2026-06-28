# modules/vetting_engine.py
"""Simple vetting engine for job listings."""

import hashlib
from typing import List, Dict, Optional

from core.string_constants import (
    SENIOR_INDICATORS,
    JUNIOR_INDICATORS,
    LANGUAGE_INDICATORS
)


class VettingEngine:
    """
    Simple vetting engine that:
    1. Validates job listings (not empty, has URL, etc.)
    2. Detects experience level (junior/mid/senior)
    3. Detects language requirements
    4. Generates stable job IDs
    """
    
    def vet_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Vet a list of jobs. Returns only valid, enriched jobs."""
        vetted = []
        for job in jobs:
            enriched = self._vet_single(job)
            if enriched:
                vetted.append(enriched)
        return vetted
    
    def _vet_single(self, job: Dict) -> Optional[Dict]:
        """Vet a single job. Returns enriched job or None if invalid."""
        # 1. Basic validation
        if not self._is_valid(job):
            return None
        
        # 2. Add metadata
        job['experience_level'] = self._detect_experience(job)
        job['languages'] = self._detect_languages(job)
        job['job_id'] = self._generate_job_id(job)
        
        return job
    
    def _is_valid(self, job: Dict) -> bool:
        """Check if job is valid."""
        # Must have a title
        title = job.get('title', '').strip()
        if len(title) < 3:
            return False
        
        # Must have a URL
        url = job.get('url', '')
        if not url:
            return False
        
        # Skip navigation/boilerplate
        invalid_titles = {'home', 'about', 'contact', 'careers', 'jobs', 'apply', 'back'}
        if title.lower() in invalid_titles:
            return False
        
        return True
    
    def _detect_experience(self, job: Dict) -> str:
        """Detect experience level from job data."""
        text = f"{job.get('title', '')} {job.get('context', '')}".lower()
        
        if any(word in text for word in SENIOR_INDICATORS):
            return 'senior'
        elif any(word in text for word in JUNIOR_INDICATORS):
            return 'junior'
        else:
            return 'mid'
    
    def _detect_languages(self, job: Dict) -> List[str]:
        """Detect language requirements."""
        text = f"{job.get('title', '')} {job.get('context', '')}".lower()
        languages = []
        
        for language, indicators in LANGUAGE_INDICATORS.items():
            if any(indicator in text for indicator in indicators):
                languages.append(language)
        
        return languages
    
    def _generate_job_id(self, job: Dict) -> str:
        """Generate a stable ID for a job."""
        url = job.get('url', '')
        if url:
            return hashlib.md5(url.encode()).hexdigest()
        
        # Fallback: hash company + title
        company = job.get('company', '')
        title = job.get('title', '')
        return hashlib.md5(f"{company}|{title}".encode()).hexdigest()