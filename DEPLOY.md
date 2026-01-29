```markdown
# DEPLOYMENT ИНСТРУКЦИЯ

## Требования к серверу
- Ubuntu 24.04 LTS (чистый VPS)
- Доступ root или sudo-пользователь
- Минимум 2 ГБ RAM, 20 ГБ SSD
- Открытые порты: 22 (SSH), 80 (HTTP), 443 (HTTPS)

## 1. Подготовка сервера
```bash
# Создаём пользователя (если нет)
adduser user_name
usermod -aG sudo user_name

# Переключаемся
su - user_name

# Обновляем систему
sudo apt update && sudo apt upgrade -y
sudo apt install git curl nano -y

# Клонируем репозиторий
git clone https://github.com/AlexeyKhaustov/fitness.git /opt/fitness_app/fitness
cd /opt/fitness_app/fitness
```

## 2. Настройка .env
Создай/отредактируй `.env`:
```env
# Django
DJANGO_SECRET_KEY=твой_очень_длинный_секрет
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=name.ru,www.name.ru,Здесь_IP,localhost,127.0.0.1

# PostgreSQL
POSTGRES_DB=fitness_db
POSTGRES_USER=fitness_user
POSTGRES_PASSWORD=сильный_пароль_2026
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Дубли для совместимости
DB_NAME=fitness_db
DB_USER=fitness_user
DB_PASSWORD=сильный_пароль_2026
DB_HOST=db
DB_PORT=5432
```

## 3. Настройка DNS (AdminVPS или регистратор)
- A-запись: fitnessvideo.ru → IP сервера
- A-запись: www.fitnessvideo.ru → IP сервера
- MX: mail.fitnessvideo.ru (приоритет 10), A → IP сервера
- TXT (SPF): "v=spf1 ip4:ВАШ_IP mx ~all"

## 4. UFW (фаервол)
```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

## 5. Docker + docker-compose
```bash
# Установка Docker (если нет)
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER
newgrp docker
```

## 6. Nginx + Certbot
```bash
# Запускаем первый раз без SSL (только 80)
docker-compose up -d

# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получаем сертификат (nginx должен быть остановлен или порт 80 свободен)
sudo certbot certonly --standalone -d fitnessvideo.ru -d www.fitnessvideo.ru \
  --email твой@email.ru --agree-tos --non-interactive

# Копируем сертификаты в проект
sudo mkdir -p certs
sudo cp /etc/letsencrypt/live/fitnessvideo.ru/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/fitnessvideo.ru/privkey.pem certs/
sudo chown fitness:fitness certs/*
```

## 7. Финальная конфигурация
- Отредактируй `nginx.conf` (два server-блока: 80→301 + 443 ssl)
- В `docker-compose.yml` добавь volume для certs:
  ```yaml
  volumes:
    - ./certs:/app/certs:ro
  ports:
    - "80:80"
    - "443:443"
  ```

- Запуск:
```bash
docker-compose down
docker-compose up -d
```

## 8. Проверки
- https://fitnessvideo.ru → 200 OK
- http://fitnessvideo.ru → 301 → https
- docker ps → 3 контейнера Up
- docker logs fitness_web_1 → Gunicorn running
- docker logs fitness_nginx_1 → без ошибок

## 9. Дополнительно (рекомендуется)
- Автообновление сертификатов: `sudo certbot renew --dry-run`
- Fail2Ban: `sudo apt install fail2ban`
- Бэкап: cron для pg_dump + rsync media
- Обновление: git pull → docker-compose build → up -d
```

Это точная инструкция по состоянию на 27–28 января 2026.
