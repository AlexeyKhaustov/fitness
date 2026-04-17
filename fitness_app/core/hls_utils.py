# fitness_app/core/hls_utils.py

import os
import shutil
import logging
from typing import Optional

from django.conf import settings

from .storage import get_video_storage
from .ffmpeg_utils import (
    encode_hls_profile,
    MASTER_BITRATE_LADDER
)

logger = logging.getLogger(__name__)

def get_or_download_source(video, temp_dir: str) -> str:
    """Загружает исходный файл видео во временную папку."""
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


def encode_all_profiles(local_input: str, temp_dir: str, profiles: list, framerate: Optional[float] = None) -> None:
    """Кодирует все профили HLS."""
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


def _update_variant_playlist(profile, remote_base, temp_dir, storage):
    """
    Внутренняя функция: перезаписывает один вариантный плейлист,
    заменяя ссылки на сегменты свежими подписанными URL.
    """
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
            new_lines.append(line)
        else:
            # Извлекаем имя сегмента из любой ссылки (относительной или абсолютной)
            segment_name = line.split('/')[-1].split('?')[0]
            segment_remote = remote_base + segment_name
            signed_url = storage.get_signed_url(segment_remote, expires=settings.AWS_QUERYSTRING_EXPIRE)
            new_lines.append(signed_url)

    new_content = "\n".join(new_lines)
    new_local = os.path.join(temp_dir, f"new_{profile['name']}.m3u8")
    with open(new_local, 'w') as f:
        f.write(new_content)

    storage.save_file(new_local, variant_remote)
    logger.info(f"Вариантный плейлист {profile['name']} перезаписан с подписанными сегментами")


def rewrite_variant_playlists(temp_dir: str, remote_base: str, profiles: list, storage) -> None:
    """Перезаписывает все вариантные плейлисты."""
    for profile in profiles:
        _update_variant_playlist(profile, remote_base, temp_dir, storage)


def regenerate_master_playlist(temp_dir: str, remote_base: str, profiles: list, storage) -> tuple:
    """
    Создаёт мастер-плейлист с подписанными URL на вариантные плейлисты.
    Возвращает (remote_path_master, dict_variant_signed_urls).
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
    """Удаляет исходный файл видео из хранилища."""
    if video.file:
        try:
            video.file.delete(save=False)
            video.file = None
            video.save(update_fields=['file'])
            logger.info(f"Исходный файл удалён для видео {video.id}")
        except Exception as e:
            logger.warning(f"Не удалось удалить исходный файл для видео {video.id}: {e}")


def get_existing_profiles(video_id: int, storage, remote_base: str) -> list:
    """Возвращает список профилей, для которых существуют вариантные плейлисты."""
    profiles = []
    for profile in MASTER_BITRATE_LADDER:
        variant_path = remote_base + f"out_{profile['name']}.m3u8"
        logger.info(f"Проверка существования варианта: {variant_path}")
        if storage.exists(variant_path):
            profiles.append(profile)
            logger.info(f"Найден профиль {profile['name']}")
        else:
            logger.warning(f"Не найден профиль {profile['name']} по пути {variant_path}")
    return profiles