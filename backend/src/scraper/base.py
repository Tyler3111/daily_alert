"""Base scraper abstractions."""

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """Abstract scraper interface."""

    @abstractmethod
    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch job data from a source."""
