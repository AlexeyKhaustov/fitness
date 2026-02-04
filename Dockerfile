FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Создаем директории для кастомных файлов
RUN mkdir -p /app/staticfiles/admin/css /app/staticfiles/admin/js

# Копируем ВСЕ кастомные файлы
COPY static/admin/css/ /app/staticfiles/admin/css/
COPY static/admin/js/ /app/staticfiles/admin/js/

# Собираем статику Django
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "fitness_app.wsgi"]