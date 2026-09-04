"""
Topic filter for news.
Filters news by topic relevance and keywords.
"""
from typing import List, Optional, Set

from parsers.base import NewsItem


class TopicFilter:
    """Filters news by topic."""
    
    def __init__(self, include_keywords: Optional[Set[str]] = None, 
                 exclude_keywords: Optional[Set[str]] = None):
        self.include_keywords = include_keywords or set()
        self.exclude_keywords = exclude_keywords or set()
    
    def is_relevant(self, item: NewsItem) -> bool:
        """
        Check if a news item matches the topic filter.
        
        Args:
            item: NewsItem to check
            
        Returns:
            True if relevant, False otherwise
        """
        text = f"{item.title} {item.content}".lower()
        
        # Check exclude keywords first
        for keyword in self.exclude_keywords:
            if keyword.lower() in text:
                return False
        
        # If no include keywords, everything not excluded is relevant
        if not self.include_keywords:
            return True
        
        # Check include keywords
        for keyword in self.include_keywords:
            if keyword.lower() in text:
                return True
        
        return False
    
    def filter_topics(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Filter news items by topic.
        
        Args:
            items: List of NewsItem objects
            
        Returns:
            List with only topic-relevant items
        """
        return [item for item in items if self.is_relevant(item)]
    
    def add_include_keyword(self, keyword: str):
        """Add a keyword to include list."""
        self.include_keywords.add(keyword)
    
    def add_exclude_keyword(self, keyword: str):
        """Add a keyword to exclude list."""
        self.exclude_keywords.add(keyword)
    
    def clear(self):
        """Clear all keywords."""
        self.include_keywords.clear()
        self.exclude_keywords.clear()
