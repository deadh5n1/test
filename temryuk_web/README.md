# Temryuk News Web Application

Веб-приложение для сбора новостей и генерации дайджестов на базе FastAPI.

## 📋 Возможности

- **Автоматический сбор новостей** из веб-сайтов, ВКонтакте и мессенджера MAX
- **Дедупликация** новостей по URL и контенту
- **Категоризация** по темам (Общество, Экономика, Спорт и др.)
- **Фильтрация** по locality (Темрюк и район)
- **Генерация Markdown-дайджестов** каждые 3 часа
- **Веб-интерфейс** для просмотра дайджестов и управления
- **Админ-панель** с запуском сбора, статистикой и управлением источниками

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd temryuk_web
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```bash
# Сгенерируйте хэш пароля админа:
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('ваш_пароль'))"

# Вставьте полученный хэш в ADMIN_PASSWORD_HASH
```

### 3. Запуск приложения

```bash
uvicorn app.main:app --reload --port 8000
```

Приложение будет доступно по адресу: http://localhost:8000

## 📁 Структура проекта

```
temryuk_web/
├── app/                      # Основное приложение
│   ├── api/                  # API роуты
│   │   ├── routes_auth.py    # Авторизация
│   │   ├── routes_digests.py # Дайджесты (публичные)
│   │   ├── routes_sources.py # Источники (админка)
│   │   ├── routes_news.py    # Новости (админка)
│   │   └── routes_actions.py # Действия (админка)
│   ├── core/                 # Ядро
│   │   ├── database.py       # БД модели
│   │   └── security.py       # Безопасность
│   ├── services/             # Бизнес-логика
│   │   ├── news_service.py   # Сбор новостей
│   │   ├── digest_service.py # Генерация дайджестов
│   │   └── scheduler_service.py # Планировщик
│   ├── templates/            # Jinja2 шаблоны
│   └── static/               # Статические файлы
├── parsers/                  # Парсеры
│   ├── base.py              # Базовый класс
│   ├── web_parser.py        # Веб-сайты
│   ├── vk_parser.py         # ВКонтакте
│   └── max_parser.py        # MAX messenger
├── processors/               # Обработчики
│   ├── deduplicator.py      # Дедупликация
│   ├── categorizer.py       # Категоризация
│   ├── location_filter.py   # Фильтр по местности
│   └── topic_filter.py      # Фильтр по темам
├── requirements.txt
├── .env.example
└── README.md
```

## 🔐 Доступ к админке

1. Перейдите на `/login`
2. Введите пароль, указанный в `.env`
3. После входа доступны:
   - `/admin` — дашборд со статистикой
   - `/admin/sources` — управление источниками
   - `/admin/news` — просмотр всех новостей
   - `/admin/run` — ручной запуск сбора

## 📡 Добавление источников

Источники добавляются напрямую в базу данных. Пример через SQLite CLI:

```sql
INSERT INTO sources (name, url, source_type, is_active) 
VALUES ('Пример сайта', 'https://example.com/news', 'web', 1);
```

Типы источников: `web`, `vk`, `max`

## ⚙️ Настройки

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DEBUG` | Режим отладки | `False` |
| `SECRET_KEY` | Ключ для сессий | (требуется) |
| `ADMIN_PASSWORD_HASH` | Хэш пароля админа | (требуется) |
| `SCHEDULER_INTERVAL_HOURS` | Интервал сбора (часы) | `3` |
| `PARSER_TIMEOUT` | Таймаут парсеров (сек) | `30` |
| `DATABASE_URL` | Строка подключения к БД | SQLite файл |

## 🐳 Деплой на VPS с Docker

### 1. Создайте Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установите системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установите зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте код приложения
COPY . .

# Откройте порт
EXPOSE 8000

# Запустите приложение
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Создайте docker-compose.yml

```yaml
version: '3.8'

services:
  temryuk-news:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data  # Для сохранения БД
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH}
    restart: unless-stopped
```

### 3. Запустите контейнер

```bash
# Создайте .env файл с вашими настройками
echo "SECRET_KEY=your-secret-key" > .env
echo "ADMIN_PASSWORD_HASH=\$(python -c \"from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))\")" >> .env

# Запустите
docker-compose up -d
```

### 4. Настройте Nginx (опционально)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔧 Разработка

### Запуск в режиме разработки

```bash
uvicorn app.main:app --reload --port 8000
```

### Тестирование

```bash
pytest
```

## 📝 API Endpoints

### Публичные
- `GET /` — Главная страница с последними дайджестами
- `GET /digest/{id}` — Просмотр конкретного дайджеста
- `GET /digests` — Список всех дайджестов (пагинация)

### Админка (требует авторизации)
- `GET /admin` — Дашборд
- `GET /admin/sources` — Управление источниками
- `POST /admin/sources/{id}/toggle` — Вкл/выкл источник
- `GET /admin/news` — Список новостей с фильтрами
- `POST /admin/run` — Запустить сбор вручную
- `GET /admin/stats` — Статистика

## 🛠️ Технологии

- **Backend**: FastAPI (асинхронный)
- **Frontend**: Jinja2 + Tailwind CSS (CDN)
- **Database**: SQLite + aiosqlite
- **Scheduler**: APScheduler
- **Auth**: passlib (bcrypt) + itsdangerous (сессии)
- **Parsing**: aiohttp, BeautifulSoup4, Playwright (опционально)

## 📄 Лицензия

MIT
