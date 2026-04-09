# fitness_app/core/ffmpeg_utils.py
"""
Утилиты для работы с FFmpeg: определение разрешения, профили кодирования,
генерация HLS-потоков.
"""

import subprocess
import os
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# Лестница битрейтов и разрешений (от высшего к низшему)
MASTER_BITRATE_LADDER: List[Dict] = [
    {"name": "1080p", "width": 1920, "height": 1080, "video_bitrate": "4000k", "audio_bitrate": "128k"},
    {"name": "720p",  "width": 1280, "height": 720,  "video_bitrate": "2500k", "audio_bitrate": "128k"},
    {"name": "480p",  "width": 854,  "height": 480,  "video_bitrate": "1500k", "audio_bitrate": "96k"},
    {"name": "360p",  "width": 640,  "height": 360,  "video_bitrate": "800k",  "audio_bitrate": "64k"},
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


def filter_profiles(source_height: int, ladder: List[Dict]) -> List[Dict]:
    """Оставляет только профили, высота которых <= высоты исходника."""
    filtered = [p for p in ladder if p["height"] <= source_height]
    logger.info(f"Исходная высота {source_height}, отфильтровано профилей: {[p['name'] for p in filtered]}")
    return filtered


def encode_hls_profile(input_path: str, output_dir: str, profile: Dict) -> str:
    """
    Конвертирует исходное видео в один HLS-профиль.
    Возвращает относительный путь к variant.m3u8 (относительно output_dir).
    """
    variant_name = profile["name"]
    variant_m3u8 = f"out_{variant_name}.m3u8"
    segment_pattern = os.path.join(output_dir, f"out_{variant_name}_%03d.ts")
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264", "-b:v", profile["video_bitrate"],
        "-maxrate", profile["video_bitrate"],
        "-bufsize", f"{int(profile['video_bitrate'][:-1]) * 2}k",
        "-vf", f"scale={profile['width']}:{profile['height']}",
        "-c:a", "aac", "-b:a", profile["audio_bitrate"],
        "-f", "hls",
        "-hls_time", "10",
        "-hls_list_size", "0",
        "-hls_segment_filename", segment_pattern,
        os.path.join(output_dir, variant_m3u8)
    ]
    logger.info(f"Запуск кодирования профиля {variant_name}: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.info(f"Профиль {variant_name} успешно создан")
    return variant_m3u8


def create_master_playlist(output_dir: str, profiles: List[Dict], variant_files: List[str]) -> str:
    """
    Создаёт master.m3u8, который ссылается на все варианты.
    Возвращает полный путь к master.m3u8.
    """
    master_path = os.path.join(output_dir, "master.m3u8")
    with open(master_path, "w") as f:
        f.write("#EXTM3U\n#EXT-X-VERSION:3\n")
        for profile, variant_file in zip(profiles, variant_files):
            bandwidth = int(profile["video_bitrate"].replace("k", "000")) + int(profile["audio_bitrate"].replace("k", "000"))
            f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={profile["width"]}x{profile["height"]}\n')
            f.write(f"{variant_file}\n")
    logger.info(f"Создан master-плейлист: {master_path}")
    return master_path