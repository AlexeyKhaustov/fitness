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
    Конвертирует видео в адаптивный HLS и загружает в хранилище.
    Поддерживает локальное хранилище и S3 (Cloud.ru, generic).
    """
    video = Video.objects.get(id=video_id)

    if video.is_processed:
        logger.info(f"Video {video_id} уже обработано, пропускаем.")
        return

    # Получаем нужную реализацию хранилища через фабрику
    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    local_input = os.path.join(temp_dir.name, "input.mp4")

    try:
        # 1. Получаем исходный файл
        if not video.file:
            raise ValueError(f"Видео {video_id} не имеет файла")

        # Пытаемся скопировать локально, если файл уже на диске
        try:
            original_path = video.file.path
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Исходный файл не найден: {original_path}")
            shutil.copy2(original_path, local_input)
            logger.info(f"Исходный файл скопирован из локального пути: {original_path}")
        except (NotImplementedError, AttributeError, FileNotFoundError) as e:
            # Если хранилище не поддерживает path (S3) или файл не найден локально,
            # скачиваем его во временную папку через storage (метод load_file)
            logger.info(f"Скачивание файла из хранилища: {video.file.name} (причина: {e})")
            # Важно: video.file.name — это относительный путь внутри бакета (например, '2026/04/video.mp4')
            # storage.load_file ожидает remote_path
            storage.load_file(video.file.name, local_input)
            logger.info(f"Файл скачан во временную папку: {local_input}")

        # 2. Определяем разрешение и фильтруем профили
        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("Нет подходящих профилей для исходного разрешения")

        logger.info(f"Видео {video_id}: исходное разрешение {width}x{height}. "
                    f"Профили: {[p['name'] for p in profiles]}")

        # 3. Кодируем каждый профиль
        variant_files = []
        for profile in profiles:
            variant_file = encode_hls_profile(local_input, temp_dir.name, profile)
            variant_files.append(variant_file)

        # 4. Создаём master.m3u8
        master_path = create_master_playlist(temp_dir.name, profiles, variant_files)

        # 5. Загружаем все сгенерированные файлы в хранилище
        #    remote_base = 'video_id/hls/'
        remote_base = f"{video_id}/hls/"
        uploaded_files = []
        for root, dirs, files in os.walk(temp_dir.name):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, temp_dir.name)
                remote_path = remote_base + relative_path
                storage.save_file(local_file, remote_path)  # используем save_file
                uploaded_files.append(remote_path)
        logger.info(f"Загружено {len(uploaded_files)} файлов в хранилище, remote_base={remote_base}")

        # 6. Обновляем модель Video
        master_remote_path = remote_base + "master.m3u8"
        # Для S3 всегда используем подписанные URL (signed=True)
        master_url = storage.get_signed_url(master_remote_path, expires=3600)
        video.hls_master_playlist = master_url

        profile_urls = {}
        for profile in profiles:
            variant_remote = remote_base + f"out_{profile['name']}.m3u8"
            profile_urls[profile["name"]] = storage.get_signed_url(variant_remote, expires=3600)
        video.hls_profiles = profile_urls

        video.is_processed = True
        video.processing_error = ""
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error"])

        # 7. Удаляем исходный файл (экономия места)
        if video.file:
            try:
                video.file.delete(save=False)
                video.file = None
                video.save(update_fields=['file'])
                logger.info(f"Исходный файл удалён для видео {video_id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить исходный файл для видео {video_id}: {e}")

        logger.info(f"Видео {video_id} успешно обработано. Master playlist: {master_url}")

    except Exception as e:
        logger.exception(f"Ошибка при обработке видео {video_id}: {e}")
        video.is_processed = False
        video.processing_error = str(e)
        video.save(update_fields=["is_processed", "processing_error"])
        # Повторяем задачу через 60 секунд (до 3 раз)
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()
        logger.debug(f"Временная папка {temp_dir.name} удалена.")