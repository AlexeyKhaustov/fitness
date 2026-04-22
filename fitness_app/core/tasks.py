# fitness_app/core/tasks.py

import logging
from celery import shared_task
from .models import Video, MarathonVideo
from .hls_utils import process_video_to_hls_generic, refresh_video_links

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_video_to_hls(self, video_id: int):
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Video {video_id} не найдено")
        return
    if video.is_processed:
        logger.info(f"Video {video_id} уже обработано")
        return
    try:
        process_video_to_hls_generic(video, "video")   # пустой префикс → путь /{id}/hls/
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_marathon_video_to_hls(self, marathon_video_id: int):
    try:
        mv = MarathonVideo.objects.get(id=marathon_video_id)
    except MarathonVideo.DoesNotExist:
        logger.error(f"MarathonVideo {marathon_video_id} не найдено")
        return
    if mv.is_processed:
        logger.info(f"MarathonVideo {marathon_video_id} уже обработано")
        return
    try:
        process_video_to_hls_generic(mv, "marathon_video/")
    except Exception as e:
        raise self.retry(exc=e)