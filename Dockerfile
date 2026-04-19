FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости, Node.js (для Tailwind CLI) и FFmpeg
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

# Создаём директорию и исходный Tailwind CSS (если файла нет, создаём заглушку)
RUN mkdir -p ./static/tailwind && \
    if [ ! -f ./static/tailwind/input.css ]; then \
        echo '@import "tailwindcss";' > ./static/tailwind/input.css; \
    fi

# Генерируем оптимизированный CSS
RUN npx tailwindcss -i ./static/tailwind/input.css -o ./static/css/output.css --minify

# Устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём директорию для логов
RUN mkdir -p /var/log/django

# Собираем статику Django (output.css уже есть, подхватится)
RUN python manage.py collectstatic --noinput

# Команда запуска (будет переопределена в docker-compose.yml, но оставим дефолтную)
CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]