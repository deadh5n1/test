"""
Модуль парсеров для сбора новостей из различных источников.
"""

import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin
import logging

import aiohttp
from bs4 import BeautifulSoup

from .models import NewsItem, SourceConfig, ParsingConfig, SourceType

logger = logging.getLogger(__name__)


class BaseParser:
    """Базовый класс для всех парсеров."""

    def __init__(self, config: ParsingConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def start_session(self):
        """Создание HTTP сессии."""
        headers = {"User-Agent": self.config.user_agent}
        self.session = aiohttp.ClientSession(headers=headers)

    async def close_session(self):
        """Закрытие HTTP сессии."""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_url(self, url: str) -> Optional[str]:
        """Получение содержимого URL."""
        if not self.session:
            await self.start_session()

        delay = random.uniform(
            self.config.random_delay_min,
            self.config.random_delay_max,
        )
        await asyncio.sleep(delay)

        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout),
            ) as response:
                if response.status == 200:
                    return await response.text(encoding="utf-8")
                else:
                    logger.warning(f"HTTP {response.status} для {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при загрузке {url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None

    def parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Парсинг даты из строки (поддержка различных форматов)."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Популярные форматы дат
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%d %B %Y %H:%M",
            "%d %B %Y",
            "%d %b %Y %H:%M",
            "%d %b %Y",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Попытка найти дату в тексте
        date_patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
            r"(\d{4})-(\d{1,2})-(\d{1,2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if len(match.group(1)) == 4:
                        return datetime(
                            int(match.group(1)),
                            int(match.group(2)),
                            int(match.group(3)),
                        )
                    else:
                        return datetime(
                            int(match.group(3)),
                            int(match.group(2)),
                            int(match.group(1)),
                        )
                except ValueError:
                    continue

        return datetime.now()

    def create_news_item(
        self,
        source: SourceConfig,
        title: str,
        content: str,
        url: str,
        published_at: Optional[datetime] = None,
    ) -> NewsItem:
        """Создание объекта новости."""
        return NewsItem(
            id=None,
            source_id=source.id,
            source_name=source.name,
            title=title.strip(),
            content=content.strip(),
            url=url,
            published_at=published_at or datetime.now(),
            fetched_at=datetime.now(),
        )


class WebSourceParser(BaseParser):
    """Парсер для веб-сайтов администраций."""

    async def parse(self, source: SourceConfig) -> List[NewsItem]:
        """Парсинг новостей с веб-сайта."""
        if not source.url:
            logger.warning(f"Источник {source.id} не имеет URL")
            return []

        logger.info(f"Парсинг веб-источника: {source.name}")

        html = await self.fetch_url(source.url)
        if not html:
            return []

        news_items = []
        soup = BeautifulSoup(html, "html.parser")

        # Универсальный парсинг - пытаемся найти новости по общим признакам
        # Ищем ссылки на новости
        news_links = []

        # Разные возможные селекторы для новостных блоков
        selectors = [
            "article",
            ".news-item",
            ".news-card",
            ".press-release",
            "[class*='news']",
            "[class*='article']",
            "[class*='press']",
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements[: source.priority * 5]:  # Ограничение количества
                    link_tag = elem.find("a", href=True)
                    title_tag = elem.find(
                        ["h1", "h2", "h3", "h4", "a"],
                        class_=lambda x: x and ("title" in x.lower() or "news" in x.lower()) if isinstance(x, str) else False,
                    )

                    if link_tag:
                        title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
                        if title and len(title) > 5:
                            full_url = urljoin(source.url, link_tag["href"])
                            news_links.append((title, full_url, elem))
            except Exception as e:
                logger.debug(f"Селектор {selector} не сработал: {e}")

        # Если ничего не найдено, пробуем найти все ссылки в основном контенте
        if not news_links:
            main_content = soup.find("main") or soup.find("div", class_="content") or soup.body
            if main_content:
                links = main_content.find_all("a", href=True)
                for link in links[:30]:
                    title = link.get_text(strip=True)
                    if title and len(title) > 10 and len(title) < 200:
                        full_url = urljoin(source.url, link["href"])
                        news_links.append((title, full_url, None))

        # Создаём новости из найденных ссылок
        seen_urls = set()
        for title, url, elem in news_links[: source.priority * 3]:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Пытаемся найти дату
            published_at = None
            if elem:
                date_elem = elem.find(
                    ["time", "span"],
                    class_=lambda x: x and ("date" in x.lower() or "time" in x.lower()) if isinstance(x, str) else False,
                )
                if date_elem:
                    published_at = self.parse_datetime(date_elem.get_text())

            # Формируем контент
            content = title
            if elem:
                # Добавляем краткое описание если есть
                desc = elem.find("p")
                if desc:
                    content = f"{title}\n\n{desc.get_text(strip=True)}"

            news = self.create_news_item(
                source=source,
                title=title,
                content=content,
                url=url,
                published_at=published_at,
            )
            news_items.append(news)

        logger.info(f"Найдено {len(news_items)} новостей из {source.name}")
        return news_items


class VKParser(BaseParser):
    """Парсер для ВКонтакте (эмуляция, т.к. требуется API)."""

    async def parse(self, source: SourceConfig) -> List[NewsItem]:
        """Парсинг новостей из ВКонтакте."""
        if not source.url:
            logger.warning(f"Источник {source.id} не имеет URL")
            return []

        logger.info(f"Парсинг VK источника: {source.name}")

        # Для реального использования нужен VK API
        # Здесь эмулируем структуру для демонстрации

        news_items = []

        # Эмуляция данных (в реальности нужно использовать VK API)
        # Пример: https://vk.com/dev/wall.get
        mock_posts = [
            {
                "text": f"Важное сообщение от {source.name}. Следите за обновлениями.",
                "date": datetime.now() - timedelta(hours=random.randint(1, 48)),
                "url": source.url,
            },
        ]

        for post in mock_posts:
            news = NewsItem(
                id=None,
                source_id=source.id,
                source_name=source.name,
                title=post["text"][:100],
                content=post["text"],
                url=post["url"],
                published_at=post["date"],
                fetched_at=datetime.now(),
                raw_data={"type": "vk_mock"},
            )
            news_items.append(news)

        logger.info(f"Найдено {len(news_items)} постов из {source.name} (VK)")
        return news_items


class MAXParser(BaseParser):
    """Парсер для мессенджера MAX (эмуляция, т.к. требуется API)."""

    async def parse(self, source: SourceConfig) -> List[NewsItem]:
        """Парсинг новостей из каналов MAX."""
        logger.info(f"Парсинг MAX каналов: {source.name}")

        news_items = []

        # Для реального использования нужен MAX API
        # Здесь эмулируем структуру для демонстрации

        channels = source.channels or ["temryuk_official"]

        for channel in channels:
            # Эмуляция сообщений из канала
            mock_messages = [
                {
                    "text": f"Сообщение из канала {channel}. Актуальная информация для жителей.",
                    "date": datetime.now() - timedelta(hours=random.randint(1, 24)),
                    "url": f"max://{channel}/message",
                },
            ]

            for msg in mock_messages:
                news = NewsItem(
                    id=None,
                    source_id=source.id,
                    source_name=f"{source.name} ({channel})",
                    title=msg["text"][:100],
                    content=msg["text"],
                    url=msg["url"],
                    published_at=msg["date"],
                    fetched_at=datetime.now(),
                    raw_data={"type": "max_mock", "channel": channel},
                )
                news_items.append(news)

        logger.info(f"Найдено {len(news_items)} сообщений из MAX")
        return news_items


def get_parser(source_type: SourceType, config: ParsingConfig) -> BaseParser:
    """Фабрика парсеров."""
    parsers = {
        SourceType.WEB: WebSourceParser,
        SourceType.VK: VKParser,
        SourceType.MAX: MAXParser,
    }

    parser_class = parsers.get(source_type, WebSourceParser)
    return parser_class(config)
