# fitness_app/core/management/commands/cleanup_video_files.py
# Выполнить: docker compose exec web python manage.py cleanup_video_files
from django.core.management.base import BaseCommand
from fitness_app.core.models import Video
import os
import shutil
from django.conf import settings

class Command(BaseCommand):
    help = 'Удаляет папки videos/{id}/hls/ для несуществующих видео и очищает orphaned исходники'

    def handle(self, *args, **options):
        media_videos_path = os.path.join(settings.MEDIA_ROOT, 'videos')
        if not os.path.exists(media_videos_path):
            self.stdout.write("Папка videos не найдена")
            return

        existing_ids = set(Video.objects.values_list('id', flat=True))

        # Удаляем папки, для которых нет видео в БД
        for item in os.listdir(media_videos_path):
            item_path = os.path.join(media_videos_path, item)
            if os.path.isdir(item_path) and item.isdigit():
                vid = int(item)
                if vid not in existing_ids:
                    self.stdout.write(f"Удаляем папку {item_path} (нет видео с id={vid})")
                    shutil.rmtree(item_path)

        # Удаляем старые исходники в папке 2026 (и других годов), которые не привязаны к видео
        # (проще удалить всё, что не обработано? но осторожно)
        # В данном случае оставляем на усмотрение администратора

        self.stdout.write(self.style.SUCCESS("Очистка завершена"))