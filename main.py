#!/usr/bin/env python3
"""
Темрюк Дайджест - Главный асинхронный скрипт сбора новостей и генерации дайджеста

Скрипт собирает новости из настроенных источников, фильтрует их по темам и местностям,
категоризирует, генерирует дайджест и сохраняет результат в файлы и базу данных.

Использование:
    python main.py [--config CONFIG_PATH] [--demo]

Аргументы:
    --config  Путь к файлу конфигурации (по умолчанию: config.yaml)
    --demo    Запуск в демонстрационном режиме с тестовыми данными
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import logging

from src.models import Config, NewsItem, load_config
from src.database import Database
from src.parsers import get_parser
from src.filter import DigestGenerator
from src.exporter import DigestExporter
from src.logger import setup_logging


logger = logging.getLogger(__name__)


class NewsCollector:
    """Основной класс для сбора новостей и генерации дайджеста."""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.database)
        self.generator = DigestGenerator(config)
        self.exporter = DigestExporter(config)

    async def initialize(self):
        """Инициализация компонентов."""
        await self.db.initialize()
        logger.info("Инициализация завершена")

    async def collect_from_sources(self) -> List[NewsItem]:
        """Сбор новостей из всех включённых источников."""
        all_news = []

        # Фильтруем только включённые источники
        enabled_sources = [s for s in self.config.sources if s.enabled]

        if not enabled_sources:
            logger.warning("Нет включённых источников!")
            return all_news

        logger.info(f"Сбор новостей из {len(enabled_sources)} источников")

        # Создаём задачи для параллельного парсинга
        tasks = []
        for source in enabled_sources:
            parser = get_parser(source.type, self.config.parsing)
            task = asyncio.create_task(parser.parse(source))
            tasks.append((source.name, task))

        # Собираем результаты
        for source_name, task in tasks:
            try:
                news_list = await task
                logger.info(f"{source_name}: найдено {len(news_list)} новостей")

                # Сохраняем каждую новость в БД
                for news in news_list[: self.config.app.max_news_per_source]:
                    saved = await self.db.save_news(news)
                    if saved:
                        all_news.append(news)

            except Exception as e:
                logger.error(f"Ошибка парсинга {source_name}: {e}")

        logger.info(f"Всего собрано новостей: {len(all_news)}")
        return all_news

    async def get_recent_news(self) -> List[NewsItem]:
        """Получение недавних новостей из БД."""
        hours = self.config.app.time_window_hours
        news = await self.db.get_recent_news(hours=hours)
        logger.info(f"Найдено {len(news)} новостей за последние {hours} часов")
        return news

    async def generate_digest(self, news_list: List[NewsItem]) -> str:
        """Генерация дайджеста."""
        digest = self.generator.generate(news_list)
        return digest

    async def save_results(
        self, 
        digest_content: str, 
        news_list: List[NewsItem]
    ) -> dict:
        """Сохранение результатов в файлы."""
        exported = await self.exporter.export_all(digest_content, news_list)
        
        # Создаём бэкап БД если включено
        if self.config.database.backup_enabled:
            await self.db.backup()

        return exported

    async def run_demo_mode(self) -> dict:
        """Запуск в демонстрационном режиме с тестовыми данными."""
        logger.info("=== ДЕМО РЕЖИМ ===")

        # Генерируем тестовые новости
        demo_news = self._generate_demo_news()

        # Сохраняем в БД
        for news in demo_news:
            await self.db.save_news(news)

        # Генерируем дайджест
        digest = await self.generate_digest(demo_news)

        # Сохраняем результаты
        exported = await self.save_results(digest, demo_news)

        # Выводим статистику
        total_in_db = await self.db.count_news()
        
        result = {
            "demo_news_generated": len(demo_news),
            "total_news_in_db": total_in_db,
            "exported_files": {k: str(v) for k, v in exported.items()},
            "digest_preview": digest[:500] + "..." if len(digest) > 500 else digest,
        }

        return result

    def _generate_demo_news(self) -> List[NewsItem]:
        """Генерация демонстрационных новостей для теста."""
        now = datetime.now()
        demo_news = []

        # Примеры новостей для разных категорий
        demo_data = [
            {
                "title": "Штормовое предупреждение объявлено в Темрюкском районе",
                "content": "По данным Краснодарского гидрометцентра, в ближайшие сутки ожидается усиление ветра до 25 м/с. Жителям рекомендуется соблюдать осторожность.",
                "category": "Погода",
                "location": "Темрюкский район",
                "source": "Оперштаб КК",
                "hours_ago": 2,
            },
            {
                "title": "Отключение воды запланировано на завтра в станице Голубицкая",
                "content": "В связи с проведением ремонтных работ на водопроводе завтра с 9:00 до 17:00 будет отключена вода в домах по улице Ленина.",
                "category": "ЖКХ",
                "location": "станица Голубицкая",
                "source": "Администрация Темрюкского района",
                "hours_ago": 5,
            },
            {
                "title": "Новый детский сад открылся в поселке Кучугуры",
                "content": "Современное дошкольное учреждение рассчитано на 120 мест. Открытие приурочено к началу учебного года.",
                "category": "Соцсфера",
                "location": "поселок Кучугуры",
                "source": "Администрация Темрюка",
                "hours_ago": 12,
            },
            {
                "title": "Ремонт дороги завершён в поселке Тамань",
                "content": "Подрядчик завершил асфальтирование участка дороги протяжённостью 2 км. Движение транспорта восстановлено в полном объёме.",
                "category": "Инфраструктура",
                "location": "поселок Тамань",
                "source": "Администрация КК",
                "hours_ago": 24,
            },
            {
                "title": "Фестиваль вина пройдет в выходные в Темрюке",
                "content": "Традиционный праздник виноделия соберёт производителей со всего Краснодарского края. Начало в 10:00 на центральной площади.",
                "category": "События",
                "location": "Темрюк",
                "source": "Глава района (ВК)",
                "hours_ago": 6,
            },
            {
                "title": "Пожарные ликвидировали возгорание сухой травы под Анапой",
                "content": "Спасатели МЧС потушили пожар на площади 5 гектаров. Пострадавших нет. Причина возгорания устанавливается.",
                "category": "ЧС",
                "location": "Анапа",
                "source": "Оперштаб КК (ВК)",
                "hours_ago": 3,
            },
            {
                "title": "График подачи электроэнергии изменён в хуторе Белый",
                "content": "В связи с плановыми работами на подстанции возможны временные отключения света с 10:00 до 14:00.",
                "category": "ЖКХ",
                "location": "хутор Белый",
                "source": "Каналы в MAX",
                "hours_ago": 8,
            },
            {
                "title": "Выплаты семьям с детьми начнутся с понедельника",
                "content": "Новые пособия будут перечисляться на карты МИР. Обратиться за назначением можно через МФЦ или портал Госуслуг.",
                "category": "Соцсфера",
                "location": "Краснодарский край",
                "source": "Администрация КК",
                "hours_ago": 18,
            },
        ]

        for i, data in enumerate(demo_data):
            news = NewsItem(
                id=None,
                source_id=f"demo_source_{i % 3}",
                source_name=data["source"],
                title=data["title"],
                content=data["content"],
                url=f"https://example.com/news/{i + 1}",
                published_at=now - timedelta(hours=data["hours_ago"]),
                fetched_at=now,
                category=data["category"],
                location_match=data["location"],
                raw_data={"demo": True},
            )
            demo_news.append(news)

        logger.info(f"Сгенерировано {len(demo_news)} демонстрационных новостей")
        return demo_news

    async def run(self, demo_mode: bool = False) -> dict:
        """Основной метод запуска сбора и генерации дайджеста."""
        start_time = datetime.now()
        logger.info(f"Запуск Темрюк Дайджест в {'демо' if demo_mode else 'боевом'} режиме")

        try:
            # Инициализация
            await self.initialize()

            if demo_mode:
                result = await self.run_demo_mode()
            else:
                # Сбор новостей из источников
                collected_news = await self.collect_from_sources()

                # Если ничего не собрали, пробуем получить из БД
                if not collected_news:
                    logger.info("Новых новостей не найдено, используем данные из БД")
                    collected_news = await self.get_recent_news()

                # Генерация дайджеста
                digest = await self.generate_digest(collected_news)

                # Сохранение результатов
                exported = await self.save_results(digest, collected_news)

                # Статистика
                total_in_db = await self.db.count_news()

                result = {
                    "news_collected": len(collected_news),
                    "total_news_in_db": total_in_db,
                    "exported_files": {k: str(v) for k, v in exported.items()},
                    "digest_preview": digest[:500] + "..." if len(digest) > 500 else digest,
                }

            # Вывод результатов
            elapsed = (datetime.now() - start_time).total_seconds()
            result["elapsed_seconds"] = elapsed

            logger.info("=" * 50)
            logger.info("ЗАВЕРШЕНО")
            logger.info(f"Время выполнения: {elapsed:.2f} сек")
            
            if "news_collected" in result:
                logger.info(f"Собрано новостей: {result['news_collected']}")
            if "demo_news_generated" in result:
                logger.info(f"Демо новостей: {result['demo_news_generated']}")
                
            logger.info(f"Всего в БД: {result['total_news_in_db']}")
            logger.info(f"Файлы экспорта: {list(result['exported_files'].keys())}")
            logger.info("=" * 50)

            return result

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            raise
        finally:
            await self.db.close()


async def main():
    """Точка входа приложения."""
    parser = argparse.ArgumentParser(
        description="Темрюк Дайджест - сбор новостей и генерация дайджеста"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запуск в демонстрационном режиме с тестовыми данными",
    )

    args = parser.parse_args()

    # Загрузка конфигурации
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Ошибка: файл конфигурации не найден: {config_path}")
        return 1

    config = load_config(str(config_path))

    # Настройка логирования
    setup_logging(config.logging)

    # Запуск сборщика
    collector = NewsCollector(config)
    await collector.run(demo_mode=args.demo)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
