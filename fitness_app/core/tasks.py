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
    Основная задача для конвертации видео в адаптивный HLS.
    - Определяет разрешение исходного видео.
    - Выбирает подходящие профили (не выше исходного).
    - Кодирует каждый профиль во временную папку.
    - Создаёт master.m3u8.
    - Загружает все файлы в хранилище (локальное или S3).
    - Обновляет модель Video.
    - Удаляет исходный файл после успешной обработки.
    """
    video = Video.objects.get(id=video_id)

    # Проверка: если уже обработано, выходим
    if video.is_processed:
        logger.info(f"Video {video_id} уже обработано, пропускаем.")
        return

    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    local_input = os.path.join(temp_dir.name, "input.mp4")

    try:
        # 1. Получаем исходный файл (поддерживает локальные пути и S3)
        if not video.file:
            raise ValueError(f"Видео {video_id} не имеет файла")

        # Пытаемся получить локальный путь, если хранилище поддерживает
        try:
            original_path = video.file.path
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Исходный файл не найден: {original_path}")
            # Копируем во временную папку
            shutil.copy2(original_path, local_input)
            logger.info(f"Исходный файл скопирован из локального пути: {original_path}")
        except (NotImplementedError, AttributeError, FileNotFoundError) as e:
            # Если хранилище не поддерживает path (S3) или файл не найден локально,
            # скачиваем его во временную папку
            logger.info(f"Скачивание файла из хранилища: {video.file.name} (причина: {e})")
            with video.file.storage.open(video.file.name, 'rb') as f:
                with open(local_input, 'wb') as out:
                    out.write(f.read())
            logger.info(f"Файл скачан во временную папку: {local_input}")

        # 2. Определяем разрешение и фильтруем профили
        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("Нет подходящих профилей для исходного разрешения")

        logger.info(f"Видео {video_id}: исходное разрешение {width}x{height}. Будет создано профилей: {[p['name'] for p in profiles]}")

        # 3. Кодируем каждый профиль
        variant_files = []
        for profile in profiles:
            variant_file = encode_hls_profile(local_input, temp_dir.name, profile)
            variant_files.append(variant_file)

        # 4. Создаём master.m3u8
        master_path = create_master_playlist(temp_dir.name, profiles, variant_files)

        # 5. Загружаем все сгенерированные файлы в хранилище
        remote_base = f"{video_id}/hls/"
        uploaded_files = []
        for root, dirs, files in os.walk(temp_dir.name):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, temp_dir.name)
                remote_path = remote_base + relative_path
                storage.save(local_file, remote_path)
                uploaded_files.append(remote_path)
        logger.info(f"Загружено {len(uploaded_files)} файлов в хранилище, remote_base={remote_base}")

        # 6. Обновляем модель Video
        master_remote_path = remote_base + "master.m3u8"
        signed = getattr(settings, 'USE_S3', False)
        master_url = storage.get_url(master_remote_path, signed=signed)
        video.hls_master_playlist = master_url

        profile_urls = {}
        for profile in profiles:
            variant_remote = remote_base + f"out_{profile['name']}.m3u8"
            profile_urls[profile["name"]] = storage.get_url(variant_remote, signed=signed)
        video.hls_profiles = profile_urls

        video.is_processed = True
        video.processing_error = ""
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error"])

        # 7. Удаляем исходный файл, так как он больше не нужен
        if video.file:
            try:
                # Удаляем физический файл из хранилища
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
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()
        logger.debug(f"Временная папка {temp_dir.name} удалена.")