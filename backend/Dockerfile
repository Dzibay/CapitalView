# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY backend/requirements.txt .

# Устанавливаем зависимости (BuildKit cache для pip ускоряет пересборки)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt gunicorn

# Копируем код приложения и SQL для init_db
COPY backend/ .
COPY database/ /app/database/

# Порт приложения
EXPOSE 5000

# Запуск: Gunicorn + Uvicorn workers для production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:5000"]
