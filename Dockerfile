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
RUN npm install && npm list --depth=0

# Создаём директорию и input.css
RUN mkdir -p static/tailwind && \
    echo '@import "tailwindcss";' > static/tailwind/input.css && \
    cat static/tailwind/input.css

# Генерируем CSS с подробным выводом
RUN npx tailwindcss -i static/tailwind/input.css -o static/css/output.css --minify --verbose

# Удаляем node_modules
RUN rm -rf node_modules

# Копируем остальной код
COPY . .

# Устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём папку для логов и собираем статику
RUN mkdir -p /var/log/django
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]