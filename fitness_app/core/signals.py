from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Video
from .tasks import process_video_to_hls
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created or (instance.file and not instance.is_processed):
        logger.info(f"Сигнал post_save: видео {instance.id} требует обработки. Отправляем задачу после фиксации транзакции.")
        transaction.on_commit(lambda: process_video_to_hls.delay(instance.id))