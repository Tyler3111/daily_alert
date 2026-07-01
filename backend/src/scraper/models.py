# scraper/models.py
"""Data models for scraper results."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class ScrapeResult:
    """Result from scraping a single URL."""
    url_id: str
    url: str
    company: str
    success: bool
    jobs: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    elapsed: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SearchResult:
    """Result from a Google search discovery task."""
    query_id: str
    query: str
    success: bool
    discovered_urls: List[Dict] = field(default_factory=list)
    jobs: List[Dict] = field(default_factory=list)  # Jobs scraped from discovered URLs
    error: Optional[str] = None
    elapsed: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())