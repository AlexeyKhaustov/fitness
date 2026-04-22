# fitness_app/core/hls_utils.py

import os
import shutil
import tempfile
import logging
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .ffmpeg_utils import (
    filter_profiles,
    MASTER_BITRATE_LADDER,
    get_video_resolution,
    get_video_framerate,
    encode_hls_profile
)
from .storage import get_video_storage

logger = logging.getLogger(__name__)


# ----- Вспомогательные функции -----
def get_or_download_source(file_field, temp_dir: str, storage) -> str:
    """Копирует или скачивает исходный файл во временную папку."""
    local_input = os.path.join(temp_dir, "input.mp4")
    try:
        original_path = file_field.path
        if os.path.exists(original_path):
            shutil.copy2(original_path, local_input)
            logger.info(f"Исходный файл скопирован из {original_path}")
            return local_input
    except (NotImplementedError, AttributeError, FileNotFoundError):
        pass

    storage.load_file(file_field.name, local_input)
    logger.info(f"Файл скачан из хранилища: {file_field.name}")
    return local_input


def delete_original_file(obj) -> None:
    """Удаляет исходный файл у модели (если есть)."""
    if obj.file:
        try:
            obj.file.delete(save=False)
            obj.file = None
            obj.save(update_fields=['file'])
            logger.info(f"Исходный файл удалён для {obj.__class__.__name__} {obj.id}")
        except Exception as e:
            logger.warning(f"Не удалось удалить исходный файл {obj.id}: {e}")


def encode_all_profiles(local_input: str, temp_dir: str, profiles: list, framerate: Optional[float] = None) -> None:
    """Кодирует все профили HLS."""
    for profile in profiles:
        encode_hls_profile(local_input, temp_dir, profile, framerate)


def upload_all_files(temp_dir: str, remote_base: str, storage) -> None:
    """Загружает все файлы из temp_dir в хранилище, сохраняя структуру."""
    for root, _, files in os.walk(temp_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, temp_dir)
            remote_path = remote_base + relative_path
            storage.save_file(local_file, remote_path)
            logger.debug(f"Загружен {remote_path}")


def get_existing_profiles(remote_base: str, storage) -> list:
    """Возвращает список профилей, для которых существуют вариантные плейлисты."""
    profiles = []
    for profile in MASTER_BITRATE_LADDER:
        variant_path = remote_base + f"out_{profile['name']}.m3u8"
        if storage.exists(variant_path):
            profiles.append(profile)
            logger.info(f"Найден профиль {profile['name']} по пути {variant_path}")
        else:
            logger.warning(f"Не найден профиль {profile['name']} по пути {variant_path}")
    return profiles


def _update_variant_playlist(profile, remote_base: str, temp_dir: str, storage, expires: int) -> None:
    """Перезаписывает вариантный плейлист, заменяя сегменты на подписанные URL."""
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
            segment_name = line.split('/')[-1].split('?')[0]
            segment_remote = remote_base + segment_name
            signed_url = storage.get_signed_url(segment_remote, expires=expires)
            new_lines.append(signed_url)

    new_content = "\n".join(new_lines)
    new_local = os.path.join(temp_dir, f"new_{profile['name']}.m3u8")
    with open(new_local, 'w') as f:
        f.write(new_content)

    storage.save_file(new_local, variant_remote)
    logger.info(f"Плейлист {profile['name']} перезаписан с подписанными сегментами")


def rewrite_variant_playlists(remote_base: str, profiles: list, storage, expires: int, temp_dir: str) -> None:
    """Перезаписывает все вариантные плейлисты."""
    for profile in profiles:
        _update_variant_playlist(profile, remote_base, temp_dir, storage, expires)


def regenerate_master_playlist(remote_base: str, profiles: list, storage, expires: int, temp_dir: str) -> tuple:
    """Создаёт мастер-плейлист с подписанными URL на варианты."""
    variant_signed_urls = {}
    for profile in profiles:
        variant_remote = remote_base + f"out_{profile['name']}.m3u8"
        variant_signed_urls[profile['name']] = storage.get_signed_url(variant_remote, expires=expires)

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
    logger.info("Мастер-плейлист перезаписан")
    return master_remote, variant_signed_urls


# ----- Универсальная обработка и обновление ссылок -----
def process_video_to_hls_generic(obj, remote_base_prefix: str) -> None:
    """
    Универсальная функция обработки видео в HLS.
    obj: экземпляр Video или MarathonVideo.
    remote_base_prefix: префикс пути в хранилище (например, '' для Video, 'marathon_video/' для MarathonVideo).
    """
    storage = get_video_storage()
    with tempfile.TemporaryDirectory(prefix=f"hls_{obj.id}_") as temp_dir:
        try:
            local_input = get_or_download_source(obj.file, temp_dir, storage)

            width, height = get_video_resolution(local_input)
            framerate = get_video_framerate(local_input)
            profiles = filter_profiles(height, MASTER_BITRATE_LADDER)
            if not profiles:
                raise RuntimeError("Нет подходящих профилей")

            logger.info(f"Обработка {obj.__class__.__name__} {obj.id}: {width}x{height}, профили: {[p['name'] for p in profiles]}")

            encode_all_profiles(local_input, temp_dir, profiles, framerate)

            remote_base = f"{remote_base_prefix}{obj.id}/hls/"
            upload_all_files(temp_dir, remote_base, storage)

            expires = settings.AWS_QUERYSTRING_EXPIRE
            rewrite_variant_playlists(remote_base, profiles, storage, expires, temp_dir)

            master_remote, variant_signed_urls = regenerate_master_playlist(
                remote_base, profiles, storage, expires, temp_dir
            )

            obj.hls_master_playlist = storage.get_signed_url(master_remote, expires=expires)
            obj.hls_profiles = variant_signed_urls
            obj.is_processed = True
            obj.processing_error = ""
            obj.hls_links_refreshed_at = timezone.now()
            obj.hls_last_ttl = expires
            obj.save(update_fields=[
                "hls_master_playlist", "hls_profiles", "is_processed",
                "processing_error", "hls_links_refreshed_at", "hls_last_ttl"
            ])

            delete_original_file(obj)
            logger.info(f"{obj.__class__.__name__} {obj.id} успешно обработано")

        except Exception as e:
            logger.exception(f"Ошибка обработки {obj.__class__.__name__} {obj.id}: {e}")
            obj.is_processed = False
            obj.processing_error = str(e)
            obj.save(update_fields=["is_processed", "processing_error"])
            raise


def refresh_video_links_generic(obj, remote_base: str, expires: int) -> bool:
    """
    Универсальная перегенерация подписанных ссылок для уже обработанного видео.
    """
    if not obj.is_processed:
        logger.warning(f"{obj.__class__.__name__} {obj.id} не обработано")
        return False

    storage = get_video_storage()
    profiles = get_existing_profiles(remote_base, storage)
    if not profiles:
        logger.error(f"Для {obj.__class__.__name__} {obj.id} нет вариантных плейлистов")
        return False

    logger.info(f"Обновление ссылок для {obj.__class__.__name__} {obj.id}, профили: {[p['name'] for p in profiles]}")

    try:
        with tempfile.TemporaryDirectory(prefix=f"refresh_{obj.id}_") as temp_dir:
            rewrite_variant_playlists(remote_base, profiles, storage, expires, temp_dir)
            master_remote, variant_signed_urls = regenerate_master_playlist(
                remote_base, profiles, storage, expires, temp_dir
            )

            obj.hls_master_playlist = storage.get_signed_url(master_remote, expires=expires)
            obj.hls_profiles = variant_signed_urls
            obj.hls_links_refreshed_at = timezone.now()
            obj.hls_last_ttl = expires
            obj.save(update_fields=[
                "hls_master_playlist", "hls_profiles",
                "hls_links_refreshed_at", "hls_last_ttl"
            ])
            logger.info(f"Ссылки для {obj.__class__.__name__} {obj.id} обновлены")
            return True
    except Exception as e:
        logger.exception(f"Ошибка обновления ссылок для {obj.__class__.__name__} {obj.id}: {e}")
        return False


# ----- Обёртки для конкретных моделей (для обратной совместимости) -----
def refresh_video_links(video_id: int) -> bool:
    from .models import Video
    video = Video.objects.get(id=video_id)
    return refresh_video_links_generic(video, f"{video_id}/hls/", settings.AWS_QUERYSTRING_EXPIRE)


def refresh_marathon_video_links(marathon_video_id: int) -> bool:
    from .models import MarathonVideo
    mv = MarathonVideo.objects.get(id=marathon_video_id)
    return refresh_video_links_generic(mv, f"marathon_video/{mv.id}/hls/", settings.AWS_QUERYSTRING_EXPIRE)