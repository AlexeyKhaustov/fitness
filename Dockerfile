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

# Копируем весь проект (кроме node_modules, которые уже установлены)
COPY . .

# Если файл static/tailwind/input.css отсутствует, создаём заглушку
RUN mkdir -p ./static/tailwind && \
    if [ ! -f ./static/tailwind/input.css ]; then \
        echo '@import "tailwindcss";' > ./static/tailwind/input.css; \
    fi

# Генерируем оптимизированный CSS (перезаписывает существующий)
RUN npx tailwindcss -i ./static/tailwind/input.css -o ./static/css/output.css --minify

# Удаляем node_modules, чтобы уменьшить размер образа (они не нужны в runtime)
RUN rm -rf node_modules

# Устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём папку для логов
RUN mkdir -p /var/log/django

# Собираем статику Django (подхватит output.css)
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "fitness_app.asgi:application", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600"]