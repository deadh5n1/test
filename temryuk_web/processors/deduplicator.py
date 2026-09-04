"""
News deduplicator.
Checks for duplicate news items based on content similarity.
"""
import hashlib
from typing import List, Set

from parsers.base import NewsItem


class Deduplicator:
    """Removes duplicate news items."""
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
    
    def is_duplicate(self, item: NewsItem) -> bool:
        """
        Check if a news item is a duplicate.
        
        Args:
            item: NewsItem to check
            
        Returns:
            True if duplicate, False otherwise
        """
        # Check by URL
        if item.url in self.seen_urls:
            return True
        
        # Check by content hash
        content_hash = self._hash_content(item.title, item.content)
        if content_hash in self.seen_hashes:
            return True
        
        # Not a duplicate - add to seen sets
        self.seen_urls.add(item.url)
        self.seen_hashes.add(content_hash)
        
        return False
    
    def filter_duplicates(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Filter out duplicates from a list of news items.
        
        Args:
            items: List of NewsItem objects
            
        Returns:
            List with duplicates removed
        """
        unique_items = []
        
        for item in items:
            if not self.is_duplicate(item):
                unique_items.append(item)
        
        return unique_items
    
    def _hash_content(self, title: str, content: str) -> str:
        """Create a hash of title and content for comparison."""
        text = f"{title.lower().strip()}|{content.lower().strip()[:500]}"
        return hashlib.md5(text.encode()).hexdigest()
    
    def reset(self):
        """Clear all seen items."""
        self.seen_urls.clear()
        self.seen_hashes.clear()
