# fitness_app/core/tasks.py

import os
import shutil
import tempfile
import logging
from celery import shared_task
from django.conf import settings
from .models import Video
from .storage import get_video_storage
from .ffmpeg_utils import (
    get_video_resolution,
    filter_profiles,
    encode_hls_profile,
    create_master_playlist,
    MASTER_BITRATE_LADDER
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_video_to_hls(self, video_id: int):
    """
    Асинхронная задача для конвертации видео в HLS формат.
    """
    video = Video.objects.get(id=video_id)

    # Если уже обработано — выходим
    if video.is_processed:
        logger.info(f"Video {video_id} already processed, skipping.")
        return

    # Получаем экземпляр хранилища (локальное или S3)
    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    local_input = os.path.join(temp_dir.name, "input.mp4")

    try:
        # --- 1. Получение исходного файла ---
        if not video.file:
            raise ValueError(f"Video {video_id} has no file")

        # Пытаемся получить локальный путь (если файл локальный)
        try:
            original_path = video.file.path
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Source file not found: {original_path}")
            shutil.copy2(original_path, local_input)
            logger.info(f"Copied from local path: {original_path}")
        except (NotImplementedError, AttributeError, FileNotFoundError) as e:
            # Если файл в S3 или путь недоступен — скачиваем через storage
            logger.info(f"Downloading file from storage: {video.file.name} (reason: {e})")
            # Используем стандартный Django storage (video.file.storage) для открытия
            # Поскольку наш storage также реализует open, это должно работать
            with video.file.storage.open(video.file.name, 'rb') as f:
                with open(local_input, 'wb') as out:
                    out.write(f.read())
            logger.info(f"Downloaded to temp: {local_input}")

        # --- 2. Определение разрешения ---
        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("No suitable profiles for source resolution")

        logger.info(f"Video {video_id}: resolution {width}x{height}, profiles: {[p['name'] for p in profiles]}")

        # --- 3. Кодирование каждого профиля ---
        variant_files = []
        for profile in profiles:
            variant_file = encode_hls_profile(local_input, temp_dir.name, profile)
            variant_files.append(variant_file)

        # --- 4. Создание master плейлиста ---
        master_path = create_master_playlist(temp_dir.name, profiles, variant_files)

        # --- 5. Загрузка всех файлов в хранилище ---
        remote_base = f"{video_id}/hls/"
        uploaded_files = []
        for root, dirs, files in os.walk(temp_dir.name):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, temp_dir.name)
                remote_path = remote_base + relative_path
                # Используем метод save_file (интерфейс VideoStorageInterface)
                storage.save_file(local_file, remote_path)
                uploaded_files.append(remote_path)
        logger.info(f"Uploaded {len(uploaded_files)} files to storage, remote_base={remote_base}")

        # --- 6. Обновление модели Video ---
        master_remote_path = remote_base + "master.m3u8"
        # Для S3 используем подписанный URL, для локального — обычный
        signed = getattr(settings, 'USE_S3', False)
        if signed:
            master_url = storage.get_signed_url(master_remote_path, expires=3600)
        else:
            # Для локального хранилища метод get_signed_url возвращает относительный путь
            master_url = storage.get_signed_url(master_remote_path)
        video.hls_master_playlist = master_url

        profile_urls = {}
        for profile in profiles:
            variant_remote = remote_base + f"out_{profile['name']}.m3u8"
            if signed:
                profile_urls[profile["name"]] = storage.get_signed_url(variant_remote, expires=3600)
            else:
                profile_urls[profile["name"]] = storage.get_signed_url(variant_remote)
        video.hls_profiles = profile_urls

        video.is_processed = True
        video.processing_error = ""
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error"])

        # --- 7. Удаление исходного файла (опционально) ---
        if video.file:
            try:
                video.file.delete(save=False)
                video.file = None
                video.save(update_fields=['file'])
                logger.info(f"Original file deleted for video {video_id}")
            except Exception as e:
                logger.warning(f"Failed to delete original file for video {video_id}: {e}")

        logger.info(f"Video {video_id} successfully processed. Master playlist: {master_url}")

    except Exception as e:
        logger.exception(f"Error processing video {video_id}: {e}")
        video.is_processed = False
        video.processing_error = str(e)
        video.save(update_fields=["is_processed", "processing_error"])
        # Повторяем задачу с задержкой
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()
        logger.debug(f"Temp directory {temp_dir.name} removed.")