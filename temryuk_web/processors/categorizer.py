"""
News categorizer.
Automatically assigns categories to news items based on content.
"""
from typing import Optional, Dict, List
import re

from parsers.base import NewsItem


class Categorizer:
    """Categorizes news items based on keywords."""
    
    # Category keywords (Russian)
    CATEGORIES = {
        "Общество": ["общество", "люди", "жители", "граждане", "социальный", "население"],
        "Экономика": ["экономика", "бизнес", "предприятие", "компания", "работа", "зарплата", "цены"],
        "Спорт": ["спорт", "матч", "команда", "соревнование", "чемпионат", "футбол", "победа"],
        "Происшествия": ["происшествие", "авария", "пожар", "преступление", "ДТП", "полиция"],
        "Политика": ["политика", "власть", "выборы", "губернатор", "администрация", "депутат"],
        "Культура": ["культура", "театр", "музей", "концерт", "выставка", "фестиваль"],
        "Образование": ["образование", "школа", "университет", "учеба", "студент", "экзамен"],
        "Здоровье": ["здоровье", "медицина", "больница", "врач", "лекарство", "вакцина"]
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for better performance."""
        self.patterns: Dict[str, List[re.Pattern]] = {}
        
        for category, keywords in self.CATEGORIES.items():
            self.patterns[category] = [
                re.compile(keyword, re.IGNORECASE) for keyword in keywords
            ]
    
    def categorize(self, item: NewsItem) -> Optional[str]:
        """
        Assign a category to a news item.
        
        Args:
            item: NewsItem to categorize
            
        Returns:
            Category name or None if no match
        """
        text = f"{item.title} {item.content}".lower()
        
        scores = {}
        
        for category, patterns in self.patterns.items():
            score = sum(1 for pattern in patterns if pattern.search(text))
            if score > 0:
                scores[category] = score
        
        if not scores:
            return None
        
        # Return category with highest score
        return max(scores, key=scores.get)
    
    def categorize_batch(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Categorize multiple news items.
        
        Args:
            items: List of NewsItem objects
            
        Returns:
            Same list with category field populated
        """
        for item in items:
            item.category = self.categorize(item)
        
        return items
