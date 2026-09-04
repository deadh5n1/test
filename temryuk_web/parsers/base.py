"""
Base parser interface.
All parsers should inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class NewsItem:
    """Represents a parsed news item."""
    title: str
    content: str
    url: str
    category: Optional[str] = None
    location: Optional[str] = None
    published_at: Optional[datetime] = None


class BaseParser(ABC):
    """Abstract base class for all parsers."""
    
    @abstractmethod
    async def parse(self, url: str) -> List[NewsItem]:
        """
        Parse news from the given URL.
        
        Args:
            url: Source URL to parse
            
        Returns:
            List of NewsItem objects
        """
        pass
