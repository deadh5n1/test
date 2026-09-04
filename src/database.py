"""
Модуль базы данных для хранения новостей.
"""

import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import logging

from .models import NewsItem, DatabaseConfig

logger = logging.getLogger(__name__)


class Database:
    """Асинхронный менеджер базы данных SQLite."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_path = Path(config.path)
        self.backup_folder = Path(config.backup_folder)
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Инициализация БД и создание таблиц."""
        # Создаём директорию для БД если не существует
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config.backup_enabled:
            self.backup_folder.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    published_at TIMESTAMP,
                    fetched_at TIMESTAMP NOT NULL,
                    category TEXT,
                    location_match TEXT,
                    summary TEXT,
                    raw_data TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_source 
                ON news(source_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_published 
                ON news(published_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_news_category 
                ON news(category)
            """)
            await db.commit()

        logger.info(f"База данных инициализирована: {self.db_path}")

    async def backup(self):
        """Создание резервной копии БД."""
        if not self.config.backup_enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_folder / f"news_backup_{timestamp}.db"

        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Резервная копия создана: {backup_path}")
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")

    async def save_news(self, news: NewsItem) -> bool:
        """Сохранение новости в БД. Возвращает True если новость сохранена, False если уже存在."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO news 
                    (source_id, source_name, title, content, url, 
                     published_at, fetched_at, category, location_match, summary, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        news.source_id,
                        news.source_name,
                        news.title,
                        news.content,
                        news.url,
                        news.published_at.isoformat() if news.published_at else None,
                        news.fetched_at.isoformat() if news.fetched_at else None,
                        news.category,
                        news.location_match,
                        news.summary,
                        str(news.raw_data) if news.raw_data else None,
                    ),
                )
                await db.commit()

                # Проверяем, была ли вставлена запись
                cursor = await db.execute(
                    "SELECT changes()"
                )
                changes = await cursor.fetchone()
                return changes[0] > 0

        except aiosqlite.IntegrityError:
            # URL уже существует
            return False
        except Exception as e:
            logger.error(f"Ошибка сохранения новости: {e}")
            return False

    async def get_recent_news(
        self, 
        hours: int = 48, 
        limit: int = 100
    ) -> List[NewsItem]:
        """Получение последних новостей за указанный период."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM news 
                WHERE fetched_at >= ?
                ORDER BY published_at DESC, fetched_at DESC
                LIMIT ?
                """,
                (cutoff.isoformat(), limit),
            )
            rows = await cursor.fetchall()

            news_items = []
            for row in rows:
                news_items.append(
                    NewsItem(
                        id=row["id"],
                        source_id=row["source_id"],
                        source_name=row["source_name"],
                        title=row["title"],
                        content=row["content"],
                        url=row["url"],
                        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
                        fetched_at=datetime.fromisoformat(row["fetched_at"]) if row["fetched_at"] else None,
                        category=row["category"],
                        location_match=row["location_match"],
                        summary=row["summary"],
                        raw_data=eval(row["raw_data"]) if row["raw_data"] else {},
                    )
                )
            return news_items

    async def get_news_by_source(
        self, 
        source_id: str, 
        limit: int = 30
    ) -> List[NewsItem]:
        """Получение новостей конкретного источника."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM news 
                WHERE source_id = ?
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (source_id, limit),
            )
            rows = await cursor.fetchall()

            news_items = []
            for row in rows:
                news_items.append(
                    NewsItem(
                        id=row["id"],
                        source_id=row["source_id"],
                        source_name=row["source_name"],
                        title=row["title"],
                        content=row["content"],
                        url=row["url"],
                        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
                        fetched_at=datetime.fromisoformat(row["fetched_at"]) if row["fetched_at"] else None,
                        category=row["category"],
                        location_match=row["location_match"],
                        summary=row["summary"],
                        raw_data=eval(row["raw_data"]) if row["raw_data"] else {},
                    )
                )
            return news_items

    async def count_news(self) -> int:
        """Подсчёт общего количества новостей."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM news")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def close(self):
        """Закрытие соединения с БД."""
        if self._connection:
            await self._connection.close()
            self._connection = None
