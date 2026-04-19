# ---- Стадия 1: Сборка Tailwind CSS ----
FROM node:20-alpine AS tailwind-builder

WORKDIR /app

# Копируем package.json и package-lock.json (если есть)
COPY package.json package-lock.json* ./
RUN npm ci && npm cache clean --force

# Создаём директорию для исходников Tailwind
RUN mkdir -p static/tailwind
COPY static/tailwind/input.css ./static/tailwind/input.css

# Генерируем output.css
RUN npx tailwindcss -i ./static/tailwind/input.css -o ./static/css/output.css --minify

# ---- Стадия 2: Основной Python-образ ----
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем собранный CSS из предыдущей стадии
COPY --from=tailwind-builder /app/static/css/ ./static/css/

# Копируем остальной код проекта (но не перезаписываем static/css)
COPY . .

# Удаляем исходные файлы Tailwind, если они случайно попали (они не нужны в продакшене)
RUN rm -rf static/tailwind

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Создаём папку для логов и собираем статику Django
RUN mkdir -p /var/log/django && \
    python manage.py collectstatic --noinput

CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]