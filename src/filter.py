"""
Модуль фильтрации и категоризации новостей.
"""

import re
from typing import List, Optional, Tuple
import logging

from .models import (
    NewsItem,
    Config,
    TopicFilterConfig,
    LocationFilterConfig,
    CategoryConfig,
)

logger = logging.getLogger(__name__)


class NewsFilter:
    """Фильтр новостей по темам и местностям."""

    def __init__(self, config: Config):
        self.config = config
        self.topic_filter = config.topic_filter
        self.location_filter = config.location_filter
        self.categories = config.categories

    def categorize(self, news: NewsItem) -> Optional[str]:
        """Определение категории новости по ключевым словам."""
        text = f"{news.title} {news.content}".lower()

        best_category = None
        best_priority = 0

        for cat_name, cat_config in self.categories.items():
            matches = 0
            for keyword in cat_config.keywords:
                if keyword.lower() in text:
                    matches += 1

            if matches > 0 and cat_config.priority >= best_priority:
                best_category = cat_name
                best_priority = cat_config.priority

        return best_category

    def check_location(self, news: NewsItem) -> Tuple[bool, Optional[str]]:
        """
        Проверка новости на соответствие фильтру местностей.
        Возвращает (пройдено_фильтр, найденная_местность).
        """
        if not self.location_filter.enabled:
            return True, None

        if self.location_filter.mode.value == "disabled":
            return True, None

        text = f"{news.title} {news.content}"

        # Проверяем приоритетные местности
        for location in self.location_filter.priority_locations:
            if location.lower() in text.lower():
                return True, location

        # Проверяем nearby если включено
        if self.location_filter.include_nearby:
            for location in self.location_filter.nearby_locations:
                if location.lower() in text.lower():
                    return True, location

        # Проверяем региональные ключевые слова
        for keyword in self.location_filter.regional_keywords:
            if keyword.lower() in text.lower():
                return True, keyword

        # Если режим strict - отклоняем всё что не совпало
        if self.location_filter.mode.value == "strict":
            return False, None

        # В режиме priority пропускаем но без указания местности
        return True, None

    def check_topic(self, category: Optional[str]) -> bool:
        """Проверка категории на соответствие фильтру тем."""
        if not self.topic_filter.enabled:
            return True

        if not category:
            # Если категория не определена, проверяем min_priority
            return self.topic_filter.min_priority <= 0

        # Принудительное включение
        if category in self.topic_filter.force_include:
            return True

        # Проверка наличия в allowed_topics
        if category not in self.topic_filter.allowed_topics:
            return False

        # Проверка приоритета
        cat_config = self.categories.get(category)
        if cat_config:
            return cat_config.priority >= self.topic_filter.min_priority

        return False

    def filter_news(self, news_list: List[NewsItem]) -> List[NewsItem]:
        """Применение всех фильтров к списку новостей."""
        filtered = []

        for news in news_list:
            # Категоризация
            category = self.categorize(news)
            news.category = category

            # Фильтр по местности
            location_ok, location_match = self.check_location(news)
            if not location_ok:
                logger.debug(f"Новость отклонена по местности: {news.title[:50]}")
                continue
            news.location_match = location_match

            # Фильтр по теме
            if not self.check_topic(category):
                logger.debug(f"Новость отклонена по теме: {news.title[:50]}")
                continue

            filtered.append(news)

        logger.info(
            f"Фильтрация: {len(news_list)} -> {len(filtered)} новостей"
        )
        return filtered


class DigestGenerator:
    """Генератор дайджеста из отфильтрованных новостей."""

    def __init__(self, config: Config):
        self.config = config
        self.digest_config = config.digest
        self.filter = NewsFilter(config)

    def generate_summary(self, text: str, max_words: int = 30) -> str:
        """Генерация краткого саммари текста."""
        # Удаляем лишние пробелы и переносы строк
        text = " ".join(text.split())

        # Разбиваем на предложения
        sentences = re.split(r"[.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text[:100]

        # Берём первое предложение или обрезаем по словам
        first_sentence = sentences[0]
        words = first_sentence.split()

        if len(words) <= max_words:
            return first_sentence

        return " ".join(words[:max_words]) + "..."

    def format_news_item(
        self, 
        news: NewsItem, 
        include_link: bool = True
    ) -> str:
        """Форматирование одной новости для дайджеста."""
        mode = self.digest_config.mode
        output_format = self.digest_config.output_format.value

        if mode.value == "summary":
            # Режим с саммари
            if news.summary:
                content = news.summary
            else:
                content = self.generate_summary(
                    news.content, 
                    self.digest_config.summary_max_words
                )

            if output_format == "markdown":
                line = f"• **{news.title}**\n  _{content}_"
            elif output_format == "html":
                line = f"<li><strong>{news.title}</strong><br/><em>{content}</em></li>"
            else:
                line = f"• {news.title}: {content}"

            if include_link and self.digest_config.include_original_links:
                if output_format == "markdown":
                    line += f"\n  [Источник]({news.url})"
                elif output_format == "html":
                    line += f' <a href="{news.url}">Источник</a>'
                else:
                    line += f" [{news.url}]"

        else:
            # Raw режим - только заголовок и ссылка
            if output_format == "markdown":
                line = f"• **{news.title}**"
            elif output_format == "html":
                line = f"<li><strong>{news.title}</strong></li>"
            else:
                line = f"• {news.title}"

            if include_link and self.digest_config.include_original_links:
                if output_format == "markdown":
                    line += f"\n  [Источник]({news.url})"
                elif output_format == "html":
                    line += f' <a href="{news.url}">Источник</a>'
                else:
                    line += f" [{news.url}]"

        # Добавляем источник если есть
        if news.source_name:
            if output_format == "markdown":
                line += f" — *{news.source_name}*"
            elif output_format == "html":
                line += f" — <em>{news.source_name}</em>"
            else:
                line += f" — {news.source_name}"

        return line

    def group_by_category(
        self, 
        news_list: List[NewsItem]
    ) -> dict[str, List[NewsItem]]:
        """Группировка новостей по категориям."""
        grouped = {}

        for news in news_list:
            category = news.category or "Разное"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(news)

        # Сортируем категории по приоритету
        priority_order = {
            cat_name: cat_config.priority 
            for cat_name, cat_config in self.config.categories.items()
        }
        priority_order["Разное"] = 0

        sorted_grouped = dict(
            sorted(
                grouped.items(),
                key=lambda x: priority_order.get(x[0], 0),
                reverse=True,
            )
        )

        return sorted_grouped

    def generate(self, news_list: List[NewsItem]) -> str:
        """Генерация полного дайджеста."""
        if not news_list:
            return self._generate_empty()

        # Применяем фильтры
        filtered_news = self.filter.filter_news(news_list)

        if not filtered_news:
            return self._generate_empty()

        # Группируем по категориям
        grouped = self.group_by_category(filtered_news)

        output_format = self.digest_config.output_format.value
        sections = []

        # Заголовок
        if output_format == "markdown":
            header = "# 📰 Темрюк Дайджест\n"
        elif output_format == "html":
            header = "<h1>📰 Темрюк Дайджест</h1>"
        else:
            header = "Темрюк Дайджест\n" + "=" * 40 + "\n"

        sections.append(header)

        # Секции по категориям
        for category, items in grouped.items():
            if output_format == "markdown":
                section_header = f"\n## {category}\n"
            elif output_format == "html":
                section_header = f"<h2>{category}</h2><ul>"
            else:
                section_header = f"\n{category}\n{'-' * len(category)}\n"

            section_items = []
            for news in items:
                section_items.append(self.format_news_item(news))

            if output_format == "html":
                section_content = "\n".join(section_items) + "</ul>"
            else:
                section_content = "\n".join(section_items)

            sections.append(section_header + section_content)

        # Футер с источниками
        if self.digest_config.include_sources_in_footer:
            sources = set(n.source_name for n in filtered_news if n.source_name)
            
            if output_format == "markdown":
                footer = f"\n\n---\n_Источники: {', '.join(sorted(sources))}_\n"
            elif output_format == "html":
                footer = f"<hr/><p><em>Источники: {', '.join(sorted(sources))}</em></p>"
            else:
                footer = f"\n{'-' * 40}\nИсточники: {', '.join(sorted(sources))}\n"
            
            sections.append(footer)

        return "\n".join(sections)

    def _generate_empty(self) -> str:
        """Генерация сообщения когда новостей нет."""
        output_format = self.digest_config.output_format.value

        if output_format == "markdown":
            return "# 📰 Темрюк Дайджест\n\n_За выбранный период новых новостей не найдено._"
        elif output_format == "html":
            return "<h1>📰 Темрюк Дайджест</h1><p><em>За выбранный период новых новостей не найдено.</em></p>"
        else:
            return "Темрюк Дайджест\n\nЗа выбранный период новых новостей не найдено."
