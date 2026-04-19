FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем package.json и устанавливаем npm зависимости
COPY package.json .
RUN npm install

# Копируем весь проект
COPY . .

# Создаём input.css с минимальным содержимым
RUN mkdir -p static/tailwind && \
    echo '@import "tailwindcss";' > static/tailwind/input.css

# Генерируем output.css (удаляем старый, если есть)
RUN rm -rf static/css && \
    npx tailwindcss -i static/tailwind/input.css -o static/css/output.css --minify

# Удаляем node_modules для уменьшения размера образа
RUN rm -rf node_modules

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Создаём папку для логов и собираем статику
RUN mkdir -p /var/log/django && \
    python manage.py collectstatic --noinput

CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]