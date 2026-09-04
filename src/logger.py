"""
Модуль логирования.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from .models import LoggingConfig


def setup_logging(config: LoggingConfig) -> logging.Logger:
    """Настройка логирования согласно конфигурации."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    # Очищаем существующие обработчики
    logger.handlers.clear()

    # Форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик с ротацией
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Парсим размер ротации (например "10 MB")
    rotation_size = parse_rotation_size(config.rotation)
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=rotation_size,
        backupCount=7,  # retention примерно соответствует количеству бэкапов
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def parse_rotation_size(rotation_str: str) -> int:
    """Парсинг строки размера ротации в байты."""
    parts = rotation_str.strip().split()
    if len(parts) == 1:
        return int(parts[0])
    
    value = int(parts[0])
    unit = parts[1].upper()
    
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
    }
    
    return value * multipliers.get(unit, 1)
