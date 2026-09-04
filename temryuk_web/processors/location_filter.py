"""
Location filter for news.
Filters news by geographic location (Temryuk and surrounding areas).
"""
from typing import List, Optional, Set

from parsers.base import NewsItem


class LocationFilter:
    """Filters news by location."""
    
    # Locations related to Temryuk district
    TEMRYUK_LOCATIONS = {
        "Темрюк", "Темрюкский", "Темрюкский район",
        "Сенной", "Сенная", "Порт-Кавказ", "Красный Десант",
        "Фонталовская", "Ахтанизовская", "Старотитаровская",
        "Вышестеблиевская", "Запорожская", "Переправная",
        "Курчанская", "Юбилейный", "Виноградный",
        "Голубицкая", "Ильич", "Коса Тузла"
    }
    
    def __init__(self, locations: Optional[Set[str]] = None):
        self.locations = locations or self.TEMRYUK_LOCATIONS
    
    def is_relevant(self, item: NewsItem) -> bool:
        """
        Check if a news item is relevant to Temryuk area.
        
        Args:
            item: NewsItem to check
            
        Returns:
            True if relevant, False otherwise
        """
        text = f"{item.title} {item.content}".lower()
        
        for location in self.locations:
            if location.lower() in text:
                item.location = location
                return True
        
        return False
    
    def filter_by_location(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Filter news items by location relevance.
        
        Args:
            items: List of NewsItem objects
            
        Returns:
            List with only location-relevant items
        """
        return [item for item in items if self.is_relevant(item)]
    
    def add_location(self, location: str):
        """Add a new location to the filter."""
        self.locations.add(location)
    
    def remove_location(self, location: str):
        """Remove a location from the filter."""
        self.locations.discard(location)
