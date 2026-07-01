# modules/filter_engine.py
"""Filter Engine - Applies filters and detects job attributes."""

from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


class FilterEngine:
    """
    Applies filters to job listings:
    1. Keyword matching
    2. Experience level detection
    3. Language detection
    4. Location filtering
    """
    
    # Keywords for filtering
    TECH_KEYWORDS = [
        'python', 'java', 'javascript', 'typescript', 'react', 'node',
        'backend', 'frontend', 'fullstack', 'developer', 'engineer',
        'software', 'devops', 'cloud', 'aws', 'gcp', 'azure',
        'docker', 'kubernetes', 'k8s', 'terraform', 'ansible'
    ]
    
    SENIOR_INDICATORS = [
        'senior', 'lead', 'principal', 'staff', 'manager', 'director',
        'head of', 'vp', 'vice president', 'architect'
    ]
    
    JUNIOR_INDICATORS = [
        'junior', 'entry', 'entry-level', 'associate', 'graduate',
        'intern', 'trainee', 'apprentice', 'early career'
    ]
    
    LANGUAGE_INDICATORS = {
        'english': ['english', 'eng', 'english-speaking', 'fluent english', 'eng'],
        'mandarin': ['mandarin', 'chinese', '中文', '普通话', 'putonghua', '国语'],
        'cantonese': ['cantonese', 'canton', '粤语', '廣東話', 'guangdong', '粤语']
    }
    
    def __init__(self, preferences: Optional[Dict] = None):
        self.preferences = preferences or {
            'required_keywords': ['software', 'engineer', 'developer'],
            'preferred_locations': ['Hong Kong', 'HK', '亚洲', 'Asia'],
            'min_experience': 'junior',  # junior, mid, senior
            'languages': ['english']  # english, mandarin, cantonese
        }
    
    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Apply all filters to a list of jobs.
        Returns filtered and enriched jobs.
        """
        filtered = []
        
        for job in jobs:
            # Check if job matches all filters
            if not self._matches_keywords(job):
                continue
            
            if not self._matches_location(job):
                continue
            
            if not self._matches_experience(job):
                continue
            
            if not self._matches_language(job):
                continue
            
            # Enrich with metadata
            job['experience_level'] = self.detect_experience(job)
            job['languages'] = self.detect_languages(job)
            job['match_score'] = self.calculate_match_score(job)
            
            filtered.append(job)
        
        logger.info(f"🔍 Filtered: {len(jobs)} → {len(filtered)} jobs")
        return filtered
    
    def _matches_keywords(self, job: Dict) -> bool:
        """Check if job contains required keywords."""
        required = self.preferences.get('required_keywords', [])
        if not required:
            return True
        
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('context', '')}".lower()
        
        # Require at least one match
        for keyword in required:
            if keyword.lower() in text:
                return True
        
        # Also check tech keywords
        tech_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        for tech in self.TECH_KEYWORDS:
            if tech in tech_text:
                return True
        
        return False
    
    def _matches_location(self, job: Dict) -> bool:
        """Check if job matches location preferences."""
        preferred = self.preferences.get('preferred_locations', [])
        if not preferred:
            return True
        
        location = job.get('location', '').lower()
        if not location:
            return True  # Remote jobs are okay
        
        for loc in preferred:
            if loc.lower() in location:
                return True
        
        return False
    
    def _matches_experience(self, job: Dict) -> bool:
        """Check if job matches experience preferences."""
        min_exp = self.preferences.get('min_experience', 'junior')
        
        # Detect experience level
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('context', '')}".lower()
        
        if min_exp == 'senior':
            # Require senior indicators
            return any(indicator in text for indicator in self.SENIOR_INDICATORS)
        elif min_exp == 'mid':
            # Allow mid and senior
            if any(indicator in text for indicator in self.JUNIOR_INDICATORS):
                return False
            return True  # Accept mid or senior
        else:
            # junior - accept all
            return True
    
    def _matches_language(self, job: Dict) -> bool:
        """Check if job matches language requirements."""
        required_langs = self.preferences.get('languages', [])
        if not required_langs:
            return True
        
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('context', '')}".lower()
        
        for lang in required_langs:
            if lang in self.LANGUAGE_INDICATORS:
                indicators = self.LANGUAGE_INDICATORS[lang]
                if any(indicator in text for indicator in indicators):
                    return True
        
        return False
    
    def detect_experience(self, job: Dict) -> str:
        """Detect experience level from job data."""
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('context', '')}".lower()
        
        if any(indicator in text for indicator in self.SENIOR_INDICATORS):
            return 'senior'
        elif any(indicator in text for indicator in self.JUNIOR_INDICATORS):
            return 'junior'
        else:
            return 'mid'
    
    def detect_languages(self, job: Dict) -> List[str]:
        """Detect language requirements from job data."""
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('context', '')}".lower()
        languages = []
        
        for language, indicators in self.LANGUAGE_INDICATORS.items():
            if any(indicator in text for indicator in indicators):
                languages.append(language)
        
        return languages
    
    def calculate_match_score(self, job: Dict) -> float:
        """
        Calculate a match score (0.0 to 1.0) for a job.
        Higher scores indicate a better match.
        """
        score = 0.0
        total_weight = 0.0
        
        # Title match (weight: 0.4)
        title = job.get('title', '').lower()
        if title:
            for keyword in self.preferences.get('required_keywords', []):
                if keyword.lower() in title:
                    score += 0.4 / len(self.preferences.get('required_keywords', [1]))
            total_weight += 0.4
        
        # Description match (weight: 0.3)
        description = f"{job.get('description', '')} {job.get('context', '')}".lower()
        if description:
            tech_matches = sum(1 for tech in self.TECH_KEYWORDS if tech in description)
            if tech_matches > 0:
                score += 0.3 * min(tech_matches / 5, 1)
            total_weight += 0.3
        
        # Location match (weight: 0.2)
        location = job.get('location', '').lower()
        if location:
            for pref in self.preferences.get('preferred_locations', []):
                if pref.lower() in location:
                    score += 0.2
                    break
            total_weight += 0.2
        else:
            # Remote jobs get partial credit
            score += 0.1
            total_weight += 0.2
        
        # Language match (weight: 0.1)
        job_langs = job.get('languages', [])
        if job_langs:
            for lang in self.preferences.get('languages', []):
                if lang in job_langs:
                    score += 0.1
                    break
        total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0