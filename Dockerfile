# ---- Стадия 1: Сборка Tailwind CSS ----
FROM node:20-alpine AS tailwind-builder

WORKDIR /app

COPY package.json ./
RUN npm install && npm cache clean --force

RUN mkdir -p static/tailwind
COPY static/tailwind/input.css ./static/tailwind/input.css

RUN npx tailwindcss -i ./static/tailwind/input.css -o ./static/css/output.css --minify

# ---- Стадия 2: Основной Python-образ ----
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем только requirements.txt (для кэширования слоя с зависимостями)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем остальной код
COPY . .

# Удаляем статику, которая могла быть скопирована (заменим собранной)
RUN rm -rf static/css static/tailwind

# Копируем собранный CSS из стадии tailwind
COPY --from=tailwind-builder /app/static/css/ ./static/css/

# Создаём папку для логов (на случай отсутствия монтирования)
RUN mkdir -p /var/log/django

# collectstatic будет выполнен при запуске контейнера (в wait-for-db.sh)

# Команда по умолчанию (переопределяется в docker-compose)
CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]