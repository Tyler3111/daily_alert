from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

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

