# fitness_app/core/tasks.py

import tempfile
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Video
from .storage import get_video_storage
from .hls_utils import (
    get_or_download_source,
    encode_all_profiles,
    upload_all_files,
    rewrite_variant_playlists,
    regenerate_master_playlist,
    delete_original_file,
    get_existing_profiles,
    _update_variant_playlist,
)
from .ffmpeg_utils import (filter_profiles,
                           MASTER_BITRATE_LADDER,
                           create_master_playlist,
                           get_video_resolution,
                           )

logger = logging.getLogger(__name__)


def refresh_video_links(video_id: int) -> bool:
    """
    Перегенерирует подписанные ссылки для видео.
    Вызывается синхронно из вьюхи при необходимости.
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Видео {video_id} не найдено")
        return False

    if not video.is_processed:
        logger.warning(f"Видео {video_id} не обработано")
        return False

    storage = get_video_storage()
    remote_base = f"{video.id}/hls/"
    profiles = get_existing_profiles(video.id, storage, remote_base)
    if not profiles:
        logger.error(f"Для видео {video_id} нет вариантных плейлистов")
        return False

    logger.info(f"Обновление ссылок для видео {video_id}, профили: {[p['name'] for p in profiles]}")

    try:
        with tempfile.TemporaryDirectory(prefix=f"refresh_{video_id}_") as temp_dir:
            # Обновляем вариантные плейлисты (используем общую логику)
            for profile in profiles:
                # Используем ту же функцию, что и в rewrite_variant_playlists
                _update_variant_playlist(profile, remote_base, temp_dir, storage)

            # Генерируем мастер-плейлист
            master_remote, variant_signed_urls = regenerate_master_playlist(temp_dir, remote_base, profiles, storage)

            # Обновляем модель
            video.hls_master_playlist = storage.get_signed_url(master_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
            video.hls_profiles = variant_signed_urls
            video.hls_links_refreshed_at = timezone.now()
            video.save(update_fields=["hls_master_playlist", "hls_profiles", "hls_links_refreshed_at"])

            logger.info(f"Ссылки для видео {video_id} успешно обновлены")
            return True

    except Exception as e:
        logger.exception(f"Ошибка при обновлении ссылок для видео {video_id}: {e}")
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_video_to_hls(self, video_id: int):
    """
    Основная задача конвертации видео в HLS.
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Видео {video_id} не найдено")
        return

    if video.is_processed:
        logger.info(f"Видео {video_id} уже обработано")
        return

    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    try:
        local_input = get_or_download_source(video, temp_dir.name)

        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("Нет подходящих профилей")

        logger.info(f"Видео {video_id}: {width}x{height}, профили: {[p['name'] for p in profiles]}")

        encode_all_profiles(local_input, temp_dir.name, profiles)

        # Временный мастер (не обязателен, но нужен для create_master_playlist)
        variant_files = [f"out_{p['name']}.m3u8" for p in profiles]
        create_master_playlist(temp_dir.name, profiles, variant_files)

        remote_base = f"{video_id}/hls/"
        upload_all_files(temp_dir.name, remote_base, storage)

        rewrite_variant_playlists(temp_dir.name, remote_base, profiles, storage)

        master_remote, variant_signed_urls = regenerate_master_playlist(temp_dir.name, remote_base, profiles, storage)

        video.hls_master_playlist = storage.get_signed_url(master_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
        video.hls_profiles = variant_signed_urls
        video.is_processed = True
        video.processing_error = ""
        video.hls_links_refreshed_at = timezone.now()
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error", "hls_links_refreshed_at"])

        delete_original_file(video)

        logger.info(f"Видео {video_id} успешно обработано")

    except Exception as e:
        logger.exception(f"Ошибка при обработке видео {video_id}: {e}")
        video.is_processed = False
        video.processing_error = str(e)
        video.save(update_fields=["is_processed", "processing_error"])
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()