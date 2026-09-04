"""
Модуль экспорта дайджеста в файлы.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
import json

from .models import Config, NewsItem, OutputFormat

logger = logging.getLogger(__name__)


class DigestExporter:
    """Экспорт дайджеста в различные форматы файлов."""

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Получение временной метки для имени файла."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def export_markdown(
        self, 
        content: str, 
        filename: Optional[str] = None
    ) -> Path:
        """Экспорт в Markdown файл."""
        if not filename:
            timestamp = self._get_timestamp()
            filename = f"digest_{timestamp}.md"

        filepath = self.output_dir / filename

        await asyncio.to_thread(
            self._write_file,
            filepath,
            content,
            "utf-8",
        )

        logger.info(f"Markdown сохранён: {filepath}")
        return filepath

    async def export_html(
        self, 
        content: str, 
        filename: Optional[str] = None
    ) -> Path:
        """Экспорт в HTML файл с базовой стилизацией."""
        if not filename:
            timestamp = self._get_timestamp()
            filename = f"digest_{timestamp}.html"

        filepath = self.output_dir / filename

        html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Темрюк Дайджест</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c5282;
            border-bottom: 2px solid #4299e1;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2d3748;
            margin-top: 30px;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 15px;
        }}
        a {{
            color: #3182ce;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        em {{
            color: #718096;
            font-size: 0.9em;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

        full_html = html_template.format(content=content)

        await asyncio.to_thread(
            self._write_file,
            filepath,
            full_html,
            "utf-8",
        )

        logger.info(f"HTML сохранён: {filepath}")
        return filepath

    async def export_plain(
        self, 
        content: str, 
        filename: Optional[str] = None
    ) -> Path:
        """Экспорт в plain text файл."""
        if not filename:
            timestamp = self._get_timestamp()
            filename = f"digest_{timestamp}.txt"

        filepath = self.output_dir / filename

        # Конвертируем markdown-like формат в plain text
        plain_content = self._markdown_to_plain(content)

        await asyncio.to_thread(
            self._write_file,
            filepath,
            plain_content,
            "utf-8",
        )

        logger.info(f"Plain text сохранён: {filepath}")
        return filepath

    async def export_json(
        self, 
        news_list: list[NewsItem], 
        filename: Optional[str] = None
    ) -> Path:
        """Экспорт новостей в JSON формат."""
        if not filename:
            timestamp = self._get_timestamp()
            filename = f"news_{timestamp}.json"

        filepath = self.output_dir / filename

        data = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "mode": self.config.digest.mode.value,
                "output_format": self.config.digest.output_format.value,
                "time_window_hours": self.config.app.time_window_hours,
            },
            "news_count": len(news_list),
            "news": [news.to_dict() for news in news_list],
        }

        await asyncio.to_thread(
            self._write_file,
            filepath,
            json.dumps(data, ensure_ascii=False, indent=2),
            "utf-8",
        )

        logger.info(f"JSON сохранён: {filepath}")
        return filepath

    async def export_all(
        self, 
        digest_content: str, 
        news_list: list[NewsItem]
    ) -> dict[str, Path]:
        """Экспорт во все форматы согласно конфигурации."""
        exported = {}

        output_format = self.config.digest.output_format

        # Экспортируем основной формат
        if output_format == OutputFormat.MARKDOWN:
            path = await self.export_markdown(digest_content)
            exported["main"] = path
            # Дополнительно экспортируем HTML и JSON
            exported["html"] = await self.export_html(digest_content)
            exported["json"] = await self.export_json(news_list)

        elif output_format == OutputFormat.HTML:
            path = await self.export_html(digest_content)
            exported["main"] = path
            # Дополнительно экспортируем JSON
            exported["json"] = await self.export_json(news_list)

        else:  # PLAIN
            path = await self.export_plain(digest_content)
            exported["main"] = path
            # Дополнительно экспортируем JSON
            exported["json"] = await self.export_json(news_list)

        # Всегда экспортируем JSON для архива
        if "json" not in exported:
            exported["json"] = await self.export_json(news_list)

        return exported

    def _write_file(self, filepath: Path, content: str, encoding: str):
        """Запись содержимого в файл (синхронная)."""
        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)

    def _markdown_to_plain(self, content: str) -> str:
        """Конвертация markdown в plain text."""
        import re

        text = content

        # Удаляем заголовки markdown
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Удаляем жирный текст
        text = text.replace("**", "")

        # Удаляем курсив
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Конвертируем ссылки
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Заменяем маркеры списков
        text = re.sub(r"^• ", "- ", text, flags=re.MULTILINE)

        # Удаляем горизонтальные линии
        text = re.sub(r"^---+$", "-" * 40, text, flags=re.MULTILINE)

        return text
