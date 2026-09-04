"""
Digest generation service.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import Digest, News


class DigestService:
    """Service for generating and managing digests."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_digest(self, mode: str = "summary") -> Digest:
        """
        Generate a new digest from recent news.
        
        Args:
            mode: Generation mode - "summary" or "full"
        
        Returns:
            Generated Digest object
        """
        # Get recent news (last 24 hours or since last digest)
        last_digest = await self._get_last_digest()
        
        query = select(News).where(News.is_duplicate == False)
        
        if last_digest:
            query = query.where(News.created_at > last_digest.generated_at)
        else:
            # If no previous digest, get news from last 24 hours
            yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(News.created_at >= yesterday)
        
        query = query.order_by(News.created_at.desc())
        result = await self.db.execute(query)
        news_items = result.scalars().all()
        
        # Group news by category
        categorized_news = {}
        for news in news_items:
            category = news.category or "Другое"
            if category not in categorized_news:
                categorized_news[category] = []
            categorized_news[category].append(news)
        
        # Generate digest content
        title = f"Дайджест новостей от {datetime.utcnow().strftime('%d.%m.%Y')}"
        content = self._format_digest_content(categorized_news, mode)
        
        # Create digest record
        digest = Digest(
            title=title,
            content=content,
            news_count=len(news_items)
        )
        
        self.db.add(digest)
        await self.db.commit()
        await self.db.refresh(digest)
        
        return digest
    
    async def get_digest(self, digest_id: int) -> Optional[Digest]:
        """Get a specific digest by ID."""
        result = await self.db.execute(select(Digest).where(Digest.id == digest_id))
        return result.scalar_one_or_none()
    
    async def get_latest_digests(self, limit: int = 10) -> list:
        """Get latest digests."""
        result = await self.db.execute(
            select(Digest).order_by(desc(Digest.generated_at)).limit(limit)
        )
        return result.scalars().all()
    
    async def _get_last_digest(self) -> Optional[Digest]:
        """Get the most recent digest."""
        result = await self.db.execute(
            select(Digest).order_by(desc(Digest.generated_at)).limit(1)
        )
        return result.scalar_one_or_none()
    
    def _format_digest_content(self, categorized_news: dict, mode: str) -> str:
        """Format digest content in Markdown."""
        lines = []
        lines.append(f"# Дайджест новостей\n")
        lines.append(f"*Сгенерировано: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}*\n")
        lines.append("---\n")
        
        for category, news_list in sorted(categorized_news.items()):
            lines.append(f"\n## {category}\n")
            
            for i, news in enumerate(news_list, 1):
                if mode == "summary":
                    lines.append(f"{i}. **{news.title}** - [Источник]({news.url})\n")
                else:
                    lines.append(f"{i}. **{news.title}**\n")
                    lines.append(f"   {news.content[:200]}...\n")
                    lines.append(f"   [Читать далее]({news.url})\n")
        
        lines.append("\n---\n")
        lines.append(f"*Всего новостей: {sum(len(v) for v in categorized_news.values())}*")
        
        return "\n".join(lines)
