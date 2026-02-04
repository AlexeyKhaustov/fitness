# Makefile
.PHONY: up down build restart logs static test

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

restart:
	docker-compose restart
	./scripts/ensure_static.sh

logs:
	docker-compose logs -f

static:
	docker-compose exec web python manage.py collectstatic --noinput
	./scripts/ensure_static.sh
	docker-compose restart nginx

test:
	docker-compose exec web python manage.py test

# Полная пересборка
rebuild:
	docker-compose down
	docker-compose build
	docker-compose up -d
	sleep 5
	./scripts/ensure_static.sh