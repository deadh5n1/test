"""
News collection service.
Wraps the parser logic from the original script.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import News, Source
from parsers.base import BaseParser
from parsers.web_parser import WebParser
from parsers.vk_parser import VKParser
from parsers.max_parser import MAXParser


class CollectResult:
    """Result of news collection."""
    def __init__(self):
        self.news_collected: int = 0
        self.duplicates_found: int = 0
        self.errors: List[str] = []


class NewsService:
    """Service for collecting and managing news."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def collect_news(self, source_id: Optional[int] = None) -> CollectResult:
        """
        Collect news from sources.
        
        Args:
            source_id: If provided, collect only from this source.
                      Otherwise, collect from all active sources.
        
        Returns:
            CollectResult with statistics
        """
        result = CollectResult()
        
        # Get sources to process
        query = select(Source).where(Source.is_active == True)
        if source_id:
            query = query.where(Source.id == source_id)
        
        sources_result = await self.db.execute(query)
        sources = sources_result.scalars().all()
        
        for source in sources:
            try:
                parser = self._get_parser_for_source(source)
                if not parser:
                    result.errors.append(f"No parser for source type: {source.source_type}")
                    continue
                
                # Parse news from source
                news_items = await parser.parse(source.url)
                
                for item in news_items:
                    # Check for duplicates
                    is_duplicate = await self._check_duplicate(item.url)
                    
                    if not is_duplicate:
                        # Save news to database
                        news = News(
                            title=item.title,
                            content=item.content,
                            url=item.url,
                            source_id=source.id,
                            category=item.category,
                            location=item.location,
                            published_at=item.published_at,
                            is_duplicate=False
                        )
                        self.db.add(news)
                        result.news_collected += 1
                    else:
                        result.duplicates_found += 1
                
                # Update last sync time
                source.last_sync = datetime.utcnow()
                
            except Exception as e:
                result.errors.append(f"Error processing source {source.name}: {str(e)}")
        
        await self.db.commit()
        return result
    
    async def get_news(self, filters: dict = None) -> List[News]:
        """Get news with optional filters."""
        query = select(News).order_by(News.created_at.desc())
        
        if filters:
            if filters.get('category'):
                query = query.where(News.category == filters['category'])
            if filters.get('source_id'):
                query = query.where(News.source_id == filters['source_id'])
            if filters.get('location'):
                query = query.where(News.location.ilike(f"%{filters['location']}%"))
            if filters.get('search'):
                query = query.where(News.title.ilike(f"%{filters['search']}%"))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _get_parser_for_source(self, source: Source) -> Optional[BaseParser]:
        """Get appropriate parser for source type."""
        parsers = {
            'web': WebParser,
            'vk': VKParser,
            'max': MAXParser
        }
        
        parser_class = parsers.get(source.source_type)
        if parser_class:
            return parser_class()
        return None
    
    async def _check_duplicate(self, url: str) -> bool:
        """Check if news with this URL already exists."""
        result = await self.db.execute(select(News).where(News.url == url))
        return result.scalar_one_or_none() is not None
