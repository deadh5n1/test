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
