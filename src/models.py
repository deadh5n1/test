"""
Темрюк Дайджест - Асинхронный сборщик новостей и генератор дайджеста

Модуль конфигурации и моделей данных.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import yaml
import os


class SourceType(Enum):
    WEB = "web"
    VK = "vk"
    MAX = "max"


class DigestMode(Enum):
    SUMMARY = "summary"
    RAW = "raw"


class OutputFormat(Enum):
    MARKDOWN = "markdown"
    PLAIN = "plain"
    HTML = "html"


class LocationFilterMode(Enum):
    STRICT = "strict"
    PRIORITY = "priority"
    DISABLED = "disabled"


@dataclass
class CategoryConfig:
    priority: int
    keywords: list[str]


@dataclass
class SourceConfig:
    id: str
    name: str
    type: SourceType
    url: Optional[str] = None
    enabled: bool = True
    priority: int = 5
    channels: list[str] = field(default_factory=list)


@dataclass
class TopicFilterConfig:
    enabled: bool = True
    allowed_topics: list[str] = field(default_factory=list)
    min_priority: int = 1
    force_include: list[str] = field(default_factory=list)


@dataclass
class LocationFilterConfig:
    enabled: bool = True
    mode: LocationFilterMode = LocationFilterMode.PRIORITY
    priority_locations: list[str] = field(default_factory=list)
    include_nearby: bool = True
    nearby_locations: list[str] = field(default_factory=list)
    regional_keywords: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    name: str
    time_window_hours: int
    max_news_per_source: int
    timezone: str


@dataclass
class DigestConfig:
    mode: DigestMode
    summary_max_words: int
    include_original_links: bool
    include_sources_in_footer: bool
    output_format: OutputFormat


@dataclass
class ParsingConfig:
    request_timeout: int
    page_load_timeout: int
    random_delay_min: float
    random_delay_max: float
    user_agent: str


@dataclass
class DatabaseConfig:
    path: str
    backup_enabled: bool
    backup_folder: str


@dataclass
class LoggingConfig:
    level: str
    file: str
    rotation: str
    retention: str


@dataclass
class Config:
    app: AppConfig
    digest: DigestConfig
    sources: list[SourceConfig]
    topic_filter: TopicFilterConfig
    location_filter: LocationFilterConfig
    categories: dict[str, CategoryConfig]
    parsing: ParsingConfig
    database: DatabaseConfig
    logging: LoggingConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """Загрузка конфигурации из YAML файла."""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Парсинг общих настроек
    app = AppConfig(
        name=raw["app"]["name"],
        time_window_hours=raw["app"]["time_window_hours"],
        max_news_per_source=raw["app"]["max_news_per_source"],
        timezone=raw["app"]["timezone"],
    )

    # Парсинг настроек дайджеста
    digest = DigestConfig(
        mode=DigestMode(raw["digest"]["mode"]),
        summary_max_words=raw["digest"]["summary_max_words"],
        include_original_links=raw["digest"]["include_original_links"],
        include_sources_in_footer=raw["digest"]["include_sources_in_footer"],
        output_format=OutputFormat(raw["digest"]["output_format"]),
    )

    # Парсинг источников
    sources = []
    for src in raw["sources"]:
        sources.append(
            SourceConfig(
                id=src["id"],
                name=src["name"],
                type=SourceType(src["type"]),
                url=src.get("url"),
                enabled=src.get("enabled", True),
                priority=src.get("priority", 5),
                channels=src.get("channels", []),
            )
        )

    # Парсинг фильтра тем
    topic_filter = TopicFilterConfig(
        enabled=raw["topic_filter"]["enabled"],
        allowed_topics=raw["topic_filter"]["allowed_topics"],
        min_priority=raw["topic_filter"]["min_priority"],
        force_include=raw["topic_filter"].get("force_include", []),
    )

    # Парсинг фильтра местностей
    loc_raw = raw["location_filter"]
    location_filter = LocationFilterConfig(
        enabled=loc_raw["enabled"],
        mode=LocationFilterMode(loc_raw["mode"]),
        priority_locations=loc_raw.get("priority_locations", []),
        include_nearby=loc_raw.get("include_nearby", True),
        nearby_locations=loc_raw.get("nearby_locations", []),
        regional_keywords=loc_raw.get("regional_keywords", []),
    )

    # Парсинг категорий
    categories = {}
    for cat_name, cat_data in raw["categories"].items():
        categories[cat_name] = CategoryConfig(
            priority=cat_data["priority"],
            keywords=cat_data["keywords"],
        )

    # Парсинг настроек парсинга
    parsing = ParsingConfig(
        request_timeout=raw["parsing"]["request_timeout"],
        page_load_timeout=raw["parsing"]["page_load_timeout"],
        random_delay_min=raw["parsing"]["random_delay_min"],
        random_delay_max=raw["parsing"]["random_delay_max"],
        user_agent=raw["parsing"]["user_agent"],
    )

    # Парсинг настроек БД
    database = DatabaseConfig(
        path=raw["database"]["path"],
        backup_enabled=raw["database"]["backup_enabled"],
        backup_folder=raw["database"]["backup_folder"],
    )

    # Парсинг настроек логирования
    logging_cfg = LoggingConfig(
        level=raw["logging"]["level"],
        file=raw["logging"]["file"],
        rotation=raw["logging"]["rotation"],
        retention=raw["logging"]["retention"],
    )

    return Config(
        app=app,
        digest=digest,
        sources=sources,
        topic_filter=topic_filter,
        location_filter=location_filter,
        categories=categories,
        parsing=parsing,
        database=database,
        logging=logging_cfg,
    )


@dataclass
class NewsItem:
    """Модель новости."""
    id: Optional[int]
    source_id: str
    source_name: str
    title: str
    content: str
    url: str
    published_at: datetime
    fetched_at: datetime
    category: Optional[str] = None
    location_match: Optional[str] = None
    summary: Optional[str] = None
    raw_data: Optional[dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "category": self.category,
            "location_match": self.location_match,
            "summary": self.summary,
        }
