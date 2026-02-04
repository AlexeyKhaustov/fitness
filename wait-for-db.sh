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

# КРИТИЧНО: Гарантируем наличие кастомных статических файлов
echo "=== Гарантируем наличие кастомных статических файлов ==="

# Создаем директории
mkdir -p /app/staticfiles/admin/css /app/staticfiles/admin/js

# Если файлы существуют в исходниках, копируем их
if [ -f "/app/static/admin/css/category_admin.css" ]; then
    cp -f /app/static/admin/css/category_admin.css /app/staticfiles/admin/css/
    echo "✅ Скопирован category_admin.css"
fi

if [ -f "/app/static/admin/css/base_overrides.css" ]; then
    cp -f /app/static/admin/css/base_overrides.css /app/staticfiles/admin/css/
    echo "✅ Скопирован base_overrides.css"
fi

if [ -f "/app/static/admin/css/seoblock_admin.css" ]; then
    cp -f /app/static/admin/css/seoblock_admin.css /app/staticfiles/admin/css/
    echo "✅ Скопирован seoblock_admin.css"
fi

if [ -f "/app/static/admin/js/fontawesome_help.js" ]; then
    cp -f /app/static/admin/js/fontawesome_help.js /app/staticfiles/admin/js/
    echo "✅ Скопирован fontawesome_help.js"
fi

if [ -f "/app/static/admin/js/color_picker.js" ]; then
    cp -f /app/static/admin/js/color_picker.js /app/staticfiles/admin/js/
    echo "✅ Скопирован color_picker.js"
fi

# Проверяем
echo "=== Проверка наличия файлов ==="
ls -la /app/staticfiles/admin/css/*.css 2>/dev/null || echo "⚠️ CSS файлы не найдены"
ls -la /app/staticfiles/admin/js/*.js 2>/dev/null || echo "⚠️ JS файлы не найдены"

# Собираем статику (наши файлы уже на месте)
python manage.py collectstatic --noinput --clear

exec gunicorn --bind 0.0.0.0:8000 fitness_app.wsgi:application