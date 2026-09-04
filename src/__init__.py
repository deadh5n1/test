"""
src/__init__.py - Инициализация пакета
"""

from .models import (
    Config,
    NewsItem,
    SourceConfig,
    SourceType,
    DigestMode,
    OutputFormat,
    load_config,
)
from .database import Database
from .parsers import get_parser, WebSourceParser, VKParser, MAXParser
from .filter import NewsFilter, DigestGenerator
from .exporter import DigestExporter
from .logger import setup_logging

__all__ = [
    "Config",
    "NewsItem",
    "SourceConfig",
    "SourceType",
    "DigestMode",
    "OutputFormat",
    "load_config",
    "Database",
    "get_parser",
    "WebSourceParser",
    "VKParser",
    "MAXParser",
    "NewsFilter",
    "DigestGenerator",
    "DigestExporter",
    "setup_logging",
]
