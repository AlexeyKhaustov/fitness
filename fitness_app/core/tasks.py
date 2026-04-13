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
    Конвертирует видео в HLS и загружает в хранилище (локальное или S3).
    Для S3 генерирует подписанные URL и перезаписывает мастер-плейлист
    с полными ссылками на варианты, чтобы HLS.js мог загружать сегменты.
    """
    video = Video.objects.get(id=video_id)
    if video.is_processed:
        logger.info(f"Video {video_id} уже обработано, пропускаем.")
        return

    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    local_input = os.path.join(temp_dir.name, "input.mp4")

    try:
        # 1. Получаем исходный файл (локально или из S3)
        if not video.file:
            raise ValueError(f"Видео {video_id} не имеет файла")

        try:
            original_path = video.file.path
            if not os.path.exists(original_path):
                raise FileNotFoundError
            shutil.copy2(original_path, local_input)
            logger.info(f"Исходный файл скопирован из локального пути: {original_path}")
        except (NotImplementedError, AttributeError, FileNotFoundError):
            logger.info(f"Скачивание файла из хранилища: {video.file.name}")
            storage.load_file(video.file.name, local_input)
            logger.info(f"Файл скачан во временную папку: {local_input}")

        # 2. Определяем разрешение и фильтруем профили
        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("Нет подходящих профилей для исходного разрешения")

        logger.info(f"Видео {video_id}: {width}x{height}, профили: {[p['name'] for p in profiles]}")

        # 3. Кодируем профили
        variant_files = []
        for profile in profiles:
            variant_file = encode_hls_profile(local_input, temp_dir.name, profile)
            variant_files.append(variant_file)

        # 4. Создаём временный мастер-плейлист (с относительными путями)
        master_path = create_master_playlist(temp_dir.name, profiles, variant_files)

        # 5. Загружаем все файлы в хранилище (вариантные плейлисты и сегменты)
        remote_base = f"{video_id}/hls/"
        for root, _, files in os.walk(temp_dir.name):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, temp_dir.name)
                remote_path = remote_base + relative_path
                storage.save_file(local_file, remote_path)

        # 6. Генерируем подписанные URL для мастер-плейлиста и вариантов
        master_remote_path = remote_base + "master.m3u8"
        master_signed_url = storage.get_signed_url(master_remote_path, expires=3600)

        variant_signed_urls = {}
        for profile in profiles:
            variant_remote = remote_base + f"out_{profile['name']}.m3u8"
            variant_signed_urls[profile['name']] = storage.get_signed_url(variant_remote, expires=3600)

        # 7. Пересоздаём мастер-плейлист с полными подписанными URL
        new_master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
        for profile in profiles:
            bandwidth = int(profile['video_bitrate'].replace('k', '000')) + int(profile['audio_bitrate'].replace('k', '000'))
            resolution = f"{profile['width']}x{profile['height']}"
            new_master_lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}')
            new_master_lines.append(variant_signed_urls[profile['name']])

        new_master_content = "\n".join(new_master_lines)
        # Временно сохраняем новый мастер-плейлист локально
        new_master_local = os.path.join(temp_dir.name, "master_signed.m3u8")
        with open(new_master_local, "w") as f:
            f.write(new_master_content)

        # Загружаем его поверх старого мастер-плейлиста
        storage.save_file(new_master_local, master_remote_path)
        logger.info(f"Мастер-плейлист перезаписан с полными подписанными URL")

        # 8. Обновляем модель Video
        video.hls_master_playlist = master_signed_url
        video.hls_profiles = variant_signed_urls
        video.is_processed = True
        video.processing_error = ""
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error"])

        # 9. Удаляем исходный файл (экономия места)
        if video.file:
            try:
                video.file.delete(save=False)
                video.file = None
                video.save(update_fields=['file'])
                logger.info(f"Исходный файл удалён для видео {video_id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить исходный файл: {e}")

        logger.info(f"Видео {video_id} успешно обработано. Master playlist: {master_signed_url}")

    except Exception as e:
        logger.exception(f"Ошибка при обработке видео {video_id}: {e}")
        video.is_processed = False
        video.processing_error = str(e)
        video.save(update_fields=["is_processed", "processing_error"])
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()