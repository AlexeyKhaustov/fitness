# fitness_app/core/ffmpeg_utils.py
"""
Утилиты для работы с FFmpeg: определение разрешения, частоты кадров,
профили кодирования, генерация HLS-потоков с высоким качеством.
"""

import subprocess
import os
import logging
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

# Лестница битрейтов и разрешений (от высшего к низшему)
# Битрейты подобраны для обеспечения качества не ниже YouTube.
MASTER_BITRATE_LADDER: List[Dict] = [
    {
        "name": "1080p",
        "width": 1920,
        "height": 1080,
        "video_bitrate": "5000k",    # повысили для лучшего качества
        "audio_bitrate": "128k",
        "preset": "slow",
        "profile": "high",
        "hls_time": 10,              # длительность сегмента в секундах
    },
    {
        "name": "720p",
        "width": 1280,
        "height": 720,
        "video_bitrate": "3000k",
        "audio_bitrate": "128k",
        "preset": "slow",
        "profile": "high",
        "hls_time": 10,
    },
    {
        "name": "480p",
        "width": 854,
        "height": 480,
        "video_bitrate": "1500k",
        "audio_bitrate": "96k",
        "preset": "slow",
        "profile": "main",
        "hls_time": 10,
    },
    {
        "name": "360p",
        "width": 640,
        "height": 360,
        "video_bitrate": "800k",
        "audio_bitrate": "64k",
        "preset": "slow",
        "profile": "main",
        "hls_time": 10,
    },
]


def get_video_resolution(file_path: str) -> Tuple[int, int]:
    """
    Определяет ширину и высоту видео с помощью ffprobe.
    Возвращает (width, height).
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
        file_path
    ]
    logger.debug(f"Выполняется команда: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout.strip()
    width, height = map(int, output.split("x"))
    logger.info(f"Разрешение исходного видео: {width}x{height}")
    return width, height


def get_video_framerate(file_path: str) -> Optional[float]:
    """
    Определяет частоту кадров (fps) исходного видео с помощью ffprobe.
    Возвращает float или None, если не удалось определить.
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0"
    ]
    logger.debug(f"Выполняется команда: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if output:
            # ffprobe возвращает рациональное число, например "30000/1001" или "25/1"
            num, den = map(int, output.split('/'))
            fps = num / den
            logger.info(f"Частота кадров исходного видео: {fps:.2f} fps")
            return fps
    except Exception as e:
        logger.warning(f"Не удалось определить частоту кадров: {e}")
    return None


def filter_profiles(source_height: int, ladder: List[Dict]) -> List[Dict]:
    """Оставляет только профили, высота которых <= высоты исходника."""
    filtered = [p for p in ladder if p["height"] <= source_height]
    logger.info(f"Исходная высота {source_height}, отфильтровано профилей: {[p['name'] for p in filtered]}")
    return filtered


def encode_hls_profile(input_path: str, output_dir: str, profile: Dict, framerate: Optional[float] = None) -> str:
    """
    Конвертирует исходное видео в один HLS-профиль с улучшенными параметрами.
    Использует framerate для расчёта GOP (группы кадров), синхронизированного с hls_time.
    Возвращает относительный путь к variant.m3u8 (относительно output_dir).
    """
    variant_name = profile["name"]
    variant_m3u8 = f"out_{variant_name}.m3u8"
    segment_pattern = os.path.join(output_dir, f"out_{variant_name}_%03d.ts")

    # Определяем GOP (количество кадров между ключевыми кадрами)
    hls_time = profile.get("hls_time", 10)
    if framerate and framerate > 0:
        gop_size = int(round(framerate * hls_time))
        # Минимальный GOP = 2, максимальный = 600 (20 секунд при 30 fps)
        gop_size = max(2, min(gop_size, 600))
    else:
        # Fallback: предполагаем 25 fps (стандарт для PAL)
        gop_size = int(round(25 * hls_time))
        gop_size = max(2, min(gop_size, 600))
        logger.warning(f"Частота кадров не определена, используем GOP={gop_size} (предполагается 25 fps)")

    # Базовые параметры
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264",
        "-b:v", profile["video_bitrate"],
        "-maxrate", profile["video_bitrate"],
        "-bufsize", f"{int(profile['video_bitrate'][:-1]) * 2}k",
        "-vf", f"scale={profile['width']}:{profile['height']}:flags=lanczos",  # качественный ресайз
        "-c:a", "aac",
        "-b:a", profile["audio_bitrate"],
        "-ac", "2",                     # стерео
        "-ar", "48000",                 # частота дискретизации
        "-f", "hls",
    ]

    # Дополнительные опции из профиля
    cmd += [
        "-preset", profile.get("preset", "slow"),
        "-profile:v", profile.get("profile", "high"),
        "-g", str(gop_size),
        "-force_key_frames", f"expr:gte(t,n_forced*{hls_time})",  # ключевые кадры каждые hls_time секунд
        "-hls_time", str(hls_time),
        "-hls_list_size", "0",
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", segment_pattern,
        os.path.join(output_dir, variant_m3u8)
    ]

    logger.info(f"Запуск кодирования профиля {variant_name} (GOP={gop_size}): {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.info(f"Профиль {variant_name} успешно создан")
    return variant_m3u8


def create_master_playlist(output_dir: str, profiles: List[Dict], variant_files: List[str]) -> str:
    """
    Создаёт master.m3u8, который ссылается на все варианты.
    Добавляет информацию о кодеках (CODECS) для совместимости.
    Возвращает полный путь к master.m3u8.
    """
    master_path = os.path.join(output_dir, "master.m3u8")
    with open(master_path, "w") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        for profile, variant_file in zip(profiles, variant_files):
            bandwidth = int(profile["video_bitrate"].replace("k", "000")) + int(profile["audio_bitrate"].replace("k", "000"))
            # CODECS — для информирования плеера (не обязательно, но полезно)
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={profile["width"]}x{profile["height"]},CODECS="avc1.64001f,mp4a.40.2"\n')
            f.write(f"{variant_file}\n")
    logger.info(f"Создан master-плейлист: {master_path}")
    return master_path