# fitness_app/core/tasks.py

import os
import shutil
import tempfile
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

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


def get_or_download_source(video, temp_dir: str) -> str:
    """
    Загружает исходный файл видео во временную папку.
    Возвращает путь к локальному файлу.
    """
    local_input = os.path.join(temp_dir, "input.mp4")
    try:
        original_path = video.file.path
        if not os.path.exists(original_path):
            raise FileNotFoundError
        shutil.copy2(original_path, local_input)
        logger.info(f"Исходный файл скопирован из локального пути: {original_path}")
    except (NotImplementedError, AttributeError, FileNotFoundError) as e:
        logger.info(f"Скачивание файла из хранилища: {video.file.name} (причина: {e})")
        storage = get_video_storage()
        storage.load_file(video.file.name, local_input)
        logger.info(f"Файл скачан во временную папку: {local_input}")
    return local_input


def encode_all_profiles(local_input: str, temp_dir: str, profiles: list) -> None:
    """Кодирует все профили HLS во временную папку."""
    for profile in profiles:
        encode_hls_profile(local_input, temp_dir, profile)


def upload_all_files(temp_dir: str, remote_base: str, storage) -> None:
    """Загружает все файлы из временной папки в хранилище."""
    for root, _, files in os.walk(temp_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, temp_dir)
            remote_path = remote_base + relative_path
            storage.save_file(local_file, remote_path)
            logger.debug(f"Загружен файл: {remote_path}")


def rewrite_variant_playlists(temp_dir: str, remote_base: str, profiles: list, storage) -> None:
    """
    Перезаписывает вариантные плейлисты, заменяя ссылки на сегменты
    свежими подписанными URL (извлекает имя сегмента даже из абсолютных ссылок).
    """
    for profile in profiles:
        variant_remote = remote_base + f"out_{profile['name']}.m3u8"
        temp_variant = os.path.join(temp_dir, f"temp_{profile['name']}.m3u8")

        # Скачиваем текущий вариант
        storage.load_file(variant_remote, temp_variant)
        with open(temp_variant, 'r') as f:
            lines = f.read().splitlines()

        new_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                # Комментарии и директивы EXT* оставляем как есть
                new_lines.append(line)
            else:
                # Извлекаем имя сегмента
                segment_name = line.split('/')[-1].split('?')[0]
                segment_remote = remote_base + segment_name
                logger.debug(f"def rewrite_variant_playlists. segment_name - {segment_name}")
                logger.debug(f"def rewrite_variant_playlists. remote_base - {remote_base}")
                signed_url = storage.get_signed_url(segment_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
                new_lines.append(signed_url)

        new_content = "\n".join(new_lines)
        new_local = os.path.join(temp_dir, f"new_{profile['name']}.m3u8")
        with open(new_local, 'w') as f:
            f.write(new_content)

        # Перезаписываем вариант в хранилище
        storage.save_file(new_local, variant_remote)
        logger.info(f"Вариантный плейлист {profile['name']} перезаписан с подписанными сегментами")


def regenerate_master_playlist(temp_dir: str, remote_base: str, profiles: list, storage) -> tuple:
    """
    Создаёт новый мастер-плейлист с подписанными URL на вариантные плейлисты.
    Возвращает (remote_path_master, dict_variant_signed_urls)
    """
    variant_signed_urls = {}
    for profile in profiles:
        variant_remote = remote_base + f"out_{profile['name']}.m3u8"
        variant_signed_urls[profile['name']] = storage.get_signed_url(
            variant_remote, expires=settings.AWS_QUERYSTRING_EXPIRE
        )

    new_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for profile in profiles:
        bandwidth = int(profile['video_bitrate'].replace('k', '000')) + int(profile['audio_bitrate'].replace('k', '000'))
        resolution = f"{profile['width']}x{profile['height']}"
        new_lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}')
        new_lines.append(variant_signed_urls[profile['name']])

    new_content = "\n".join(new_lines)
    master_local = os.path.join(temp_dir, "master_signed.m3u8")
    with open(master_local, 'w') as f:
        f.write(new_content)

    master_remote = remote_base + "master.m3u8"
    storage.save_file(master_local, master_remote)
    logger.info("Мастер-плейлист перезаписан с подписанными URL вариантов")
    return master_remote, variant_signed_urls


def delete_original_file(video) -> None:
    """Удаляет исходный файл видео из хранилища (если он ещё есть)."""
    if video.file:
        try:
            video.file.delete(save=False)
            video.file = None
            video.save(update_fields=['file'])
            logger.info(f"Исходный файл удалён для видео {video.id}")
        except Exception as e:
            logger.warning(f"Не удалось удалить исходный файл для видео {video.id}: {e}")


def refresh_video_links(video_id: int) -> bool:
    """
    Перегенерирует подписанные ссылки для видео: перезаписывает вариантные плейлисты
    и мастер-плейлист, обновляет поля модели.
    Вызывается синхронно, когда срок действия ссылок подходит к концу.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Видео {video_id} не найдено при попытке обновить ссылки")
        return False

    if not video.is_processed:
        logger.warning(f"Видео {video_id} не обработано, обновление ссылок невозможно")
        return False

    storage = get_video_storage()
    remote_base = f"{video.id}/hls/"

    # --- 1. Определяем реально существующие профили с логированием ---
    profiles = []
    for profile in MASTER_BITRATE_LADDER:
        variant_path = remote_base + f"out_{profile['name']}.m3u8"
        logger.info(f"Проверка существования варианта: {variant_path}")
        if storage.exists(variant_path):
            profiles.append(profile)
            logger.info(f"Найден профиль {profile['name']}")
        else:
            logger.warning(f"Не найден профиль {profile['name']} по пути {variant_path}")

    if not profiles:
        logger.error(f"Для видео {video_id} не найдено ни одного вариантного плейлиста. Обновление невозможно.")
        return False

    logger.info(f"Обновление ссылок для видео {video_id}, профили: {[p['name'] for p in profiles]}")

    try:
        with tempfile.TemporaryDirectory(prefix=f"refresh_{video_id}_") as temp_dir:
            # --- 2. Перезаписываем вариантные плейлисты (исправленная логика) ---
            for profile in profiles:
                variant_remote = remote_base + f"out_{profile['name']}.m3u8"
                local_variant = os.path.join(temp_dir, f"out_{profile['name']}.m3u8")
                storage.load_file(variant_remote, local_variant)

                with open(local_variant, 'r') as f:
                    lines = f.read().splitlines()

                new_lines = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('#'):
                        # Комментарии и директивы EXT* оставляем как есть
                        new_lines.append(line)
                    else:
                        # Извлекаем имя сегмента (последняя часть пути)
                        segment_name = line.split('/')[-1].split('?')[0]
                        segment_remote = remote_base + segment_name
                        logger.debug(f"def refresh_video_links. segment_name - {segment_name}")
                        logger.debug(f"def refresh_video_links. remote_base - {remote_base}")
                        signed_url = storage.get_signed_url(segment_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
                        new_lines.append(signed_url)

                new_content = "\n".join(new_lines)
                new_local = os.path.join(temp_dir, f"new_{profile['name']}.m3u8")
                with open(new_local, 'w') as f:
                    f.write(new_content)
                storage.save_file(new_local, variant_remote)
                logger.debug(f"Вариантный плейлист {profile['name']} обновлён")

            # --- 3. Генерируем свежий мастер-плейлист с подписанными ссылками на варианты ---
            variant_signed_urls = {}
            for profile in profiles:
                variant_remote = remote_base + f"out_{profile['name']}.m3u8"
                variant_signed_urls[profile['name']] = storage.get_signed_url(
                    variant_remote, expires=settings.AWS_QUERYSTRING_EXPIRE
                )

            new_master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
            for profile in profiles:
                bandwidth = int(profile['video_bitrate'].replace('k', '000')) + int(profile['audio_bitrate'].replace('k', '000'))
                resolution = f"{profile['width']}x{profile['height']}"
                new_master_lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}')
                new_master_lines.append(variant_signed_urls[profile['name']])

            new_master_content = "\n".join(new_master_lines)
            new_master_local = os.path.join(temp_dir, "master_signed.m3u8")
            with open(new_master_local, 'w') as f:
                f.write(new_master_content)

            master_remote = remote_base + "master.m3u8"
            storage.save_file(new_master_local, master_remote)
            logger.info(f"Мастер-плейлист для видео {video_id} обновлён")

            # --- 4. Обновляем модель ---
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
    - Загружает исходный файл
    - Определяет разрешение и выбирает профили
    - Кодирует профили
    - Загружает все файлы в хранилище
    - Перезаписывает вариантные плейлисты с подписанными сегментами
    - Создаёт мастер-плейлист с подписанными вариантами
    - Обновляет модель Video
    - Удаляет исходный файл
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Видео {video_id} не найдено")
        return

    if video.is_processed:
        logger.info(f"Видео {video_id} уже обработано, пропускаем.")
        return

    storage = get_video_storage()
    temp_dir = tempfile.TemporaryDirectory(prefix=f"hls_{video_id}_")
    try:
        # 1. Получаем исходный файл
        local_input = get_or_download_source(video, temp_dir.name)

        # 2. Определяем разрешение и фильтруем профили
        width, height = get_video_resolution(local_input)
        profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
        if not profiles:
            raise RuntimeError("Нет подходящих профилей для исходного разрешения")
        logger.info(f"Видео {video_id}: {width}x{height}, профили: {[p['name'] for p in profiles]}")

        # 3. Кодируем профили
        encode_all_profiles(local_input, temp_dir.name, profiles)

        # 4. Создаём временный мастер-плейлист (не обязателен, но create_master_playlist удобен)
        variant_files = [f"out_{p['name']}.m3u8" for p in profiles]
        create_master_playlist(temp_dir.name, profiles, variant_files)

        # 5. Загружаем все сгенерированные файлы в хранилище
        remote_base = f"{video_id}/hls/"
        upload_all_files(temp_dir.name, remote_base, storage)

        # 6. Перезаписываем вариантные плейлисты с подписанными сегментами
        rewrite_variant_playlists(temp_dir.name, remote_base, profiles, storage)

        # 7. Генерируем финальный мастер-плейлист с подписанными вариантами
        master_remote, variant_signed_urls = regenerate_master_playlist(temp_dir.name, remote_base, profiles, storage)

        # 8. Обновляем модель Video
        video.hls_master_playlist = storage.get_signed_url(master_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
        video.hls_profiles = variant_signed_urls
        video.is_processed = True
        video.processing_error = ""
        video.hls_links_refreshed_at = timezone.now()
        video.save(update_fields=["hls_master_playlist", "hls_profiles", "is_processed", "processing_error", "hls_links_refreshed_at"])

        # 9. Удаляем исходный файл
        delete_original_file(video)

        logger.info(f"Видео {video_id} успешно обработано. Master playlist: {video.hls_master_playlist}")

    except Exception as e:
        logger.exception(f"Ошибка при обработке видео {video_id}: {e}")
        video.is_processed = False
        video.processing_error = str(e)
        video.save(update_fields=["is_processed", "processing_error"])
        raise self.retry(exc=e)

    finally:
        temp_dir.cleanup()