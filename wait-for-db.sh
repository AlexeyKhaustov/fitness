#!/bin/sh
set -e
echo "=== ОТЛАДКА ==="
env | grep POSTGRES
echo "=================="

until PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>&1; do
  echo "Ждём PostgreSQL... (ошибка выше, если есть)"
  sleep 2
done

echo "PostgreSQL готова!"
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
exec gunicorn --bind 0.0.0.0:8000 fitness_app.wsgi:application
