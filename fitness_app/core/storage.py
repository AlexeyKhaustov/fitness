# fitness_app/core/storage.py
"""
Абстракция хранилища для видеофайлов.
Позволяет легко переключаться между локальным файловым хранилищем и S3.
"""

import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from decouple import config

logger = logging.getLogger(__name__)


class VideoStorageInterface(ABC):
    """Интерфейс для работы с хранилищем видео."""

    @abstractmethod
    def save(self, local_path: str, remote_path: str) -> str:
        """
        Сохраняет файл из локальной файловой системы в хранилище.
        Возвращает публичный URL сохранённого файла.
        """
        pass

    @abstractmethod
    def load(self, remote_path: str, local_path: str) -> None:
        """Загружает файл из хранилища в локальную временную папку."""
        pass

    @abstractmethod
    def get_url(self, remote_path: str, signed: bool = False, expires: int = 3600) -> str:
        """
        Возвращает URL файла в хранилище.
        Если signed=True, генерирует временную подписанную ссылку.
        """
        pass

    @abstractmethod
    def delete(self, remote_path: str) -> None:
        """Удаляет файл из хранилища."""
        pass


class LocalVideoStorage(VideoStorageInterface):
    """Реализация для локальной файловой системы."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.path.join(settings.MEDIA_ROOT, "videos")
        logger.info(f"LocalVideoStorage инициализирован с base_path={self.base_path}")

    def save(self, local_path: str, remote_path: str) -> str:
        dest = os.path.join(self.base_path, remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)
        url = settings.MEDIA_URL + "videos/" + remote_path
        logger.debug(f"Файл скопирован: {local_path} -> {dest}, URL={url}")
        return url

    def load(self, remote_path: str, local_path: str) -> None:
        src = os.path.join(self.base_path, remote_path)
        shutil.copy2(src, local_path)
        logger.debug(f"Файл загружен: {src} -> {local_path}")

    def get_url(self, remote_path: str, signed: bool = False, expires: int = 3600) -> str:
        # Для локального хранилища подпись не нужна
        return settings.MEDIA_URL + "videos/" + remote_path

    def delete(self, remote_path: str) -> None:
        path = os.path.join(self.base_path, remote_path)
        if os.path.exists(path):
            os.remove(path)
            logger.debug(f"Удалён файл: {path}")
        else:
            logger.warning(f"Файл не найден для удаления: {path}")


class S3VideoStorage(VideoStorageInterface):
    """Реализация для S3-совместимых облачных хранилищ (Cloud.ru, VK, Selectel)."""

    def __init__(self):
        self.storage = S3Boto3Storage(
            bucket_name=config("AWS_STORAGE_BUCKET_NAME"),
            endpoint_url=config("AWS_S3_ENDPOINT_URL"),
            region_name=config("AWS_S3_REGION_NAME", default="ru-msk"),
            default_acl="private",
            querystring_auth=True,   # включаем подписанные URL
        )
        logger.info("S3VideoStorage инициализирован")

    def save(self, local_path: str, remote_path: str) -> str:
        with open(local_path, "rb") as f:
            self.storage.save(remote_path, f)
        url = self.storage.url(remote_path)
        logger.debug(f"Файл загружен в S3: {local_path} -> {remote_path}, URL={url}")
        return url

    def load(self, remote_path: str, local_path: str) -> None:
        with self.storage.open(remote_path, "rb") as f:
            content = f.read()
        with open(local_path, "wb") as f:
            f.write(content)
        logger.debug(f"Файл загружен из S3: {remote_path} -> {local_path}")

    def get_url(self, remote_path: str, signed: bool = True, expires: int = 3600) -> str:
        if signed:
            url = self.storage.url(remote_path, expire=expires)
        else:
            # Прямой публичный URL (если бакет публичный, но мы используем private)
            url = self.storage.url(remote_path)
        logger.debug(f"Сгенерирован URL для {remote_path}, signed={signed}, expires={expires}")
        return url

    def delete(self, remote_path: str) -> None:
        self.storage.delete(remote_path)
        logger.debug(f"Удалён файл из S3: {remote_path}")


def get_video_storage() -> VideoStorageInterface:
    """Фабрика, возвращающая нужную реализацию хранилища в зависимости от настроек."""
    backend = getattr(settings, "VIDEO_STORAGE_BACKEND", "local")
    logger.info(f"Выбран бэкенд хранилища: {backend}")
    if backend == "s3":
        return S3VideoStorage()
    else:
        return LocalVideoStorage()