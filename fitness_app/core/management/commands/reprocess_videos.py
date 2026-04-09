# fitness_app/core/management/commands/reprocess_videos.py

from django.core.management.base import BaseCommand
from fitness_app.core.models import Video
from fitness_app.core.tasks import process_video_to_hls
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запускает обработку всех видео, у которых is_processed=False"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Принудительно переобработать все видео (даже уже обработанные)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        if force:
            videos = Video.objects.all()
            self.stdout.write("Принудительная переобработка всех видео.")
        else:
            videos = Video.objects.filter(is_processed=False)
            self.stdout.write(f"Найдено {videos.count()} необработанных видео.")

        for video in videos:
            self.stdout.write(f"Ставим в очередь видео {video.id} - {video.title}")
            process_video_to_hls.delay(video.id)
            logger.info(f"Видео {video.id} отправлено в очередь Celery")

        self.stdout.write(self.style.SUCCESS(f"Обработка запущена для {videos.count()} видео."))