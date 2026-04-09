# fitness_app/core/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Video
from .tasks import process_video_to_hls
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Запускает задачу Celery для преобразования видео в HLS.
    Срабатывает при создании нового видео или если файл изменился,
    но видео ещё не обработано.
    """
    if created or (instance.file and not instance.is_processed):
        logger.info(f"Сигнал post_save: видео {instance.id} требует обработки. Запускаем задачу.")
        process_video_to_hls.delay(instance.id)
    else:
        logger.debug(f"Видео {instance.id} уже обработано или не имеет файла, пропускаем.")