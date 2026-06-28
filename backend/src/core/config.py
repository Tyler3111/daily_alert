# modules/config.py
import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

@dataclass
class Config:
    """Centralized configuration for all modules."""
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # LLM
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4"
    
    # Scraping
    headless: bool = True
    worker_timeout: int = 60
    max_urls_per_cycle: int = 100
    cycle_interval_hours: int = 24
    workers_per_cycle: int = 4
    
    # Discovery
    enable_discovery: bool = True
    search_keywords: List[str] = None
    
    # Database
    db_url: str = "sqlite:///jobs.db"
    
    # Search
    default_location: str = "Hong Kong"
    
    def __post_init__(self):
        if self.search_keywords is None:
            self.search_keywords = ["software", "engineer", "developer"]
    
    @classmethod
    def from_env(cls, env_file: str = ".env"):
        """Load configuration from environment variables."""
        load_dotenv(env_file)
        
        return cls(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            redis_password=os.getenv("REDIS_PASSWORD"),
            redis_db=int(os.getenv("REDIS_DB", 0)),
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            worker_timeout=int(os.getenv("WORKER_TIMEOUT", 60)),
            max_urls_per_cycle=int(os.getenv("MAX_URLS_PER_CYCLE", 100)),
            cycle_interval_hours=int(os.getenv("CYCLE_INTERVAL_HOURS", 24)),
            workers_per_cycle=int(os.getenv("WORKERS_PER_CYCLE", 4)),
            enable_discovery=os.getenv("ENABLE_DISCOVERY", "true").lower() == "true",
            search_keywords=os.getenv("SEARCH_KEYWORDS", "software,engineer,developer").split(","),
            db_url=os.getenv("DATABASE_URL", "sqlite:///jobs.db"),
            default_location=os.getenv("DEFAULT_LOCATION", "Hong Kong")
        )