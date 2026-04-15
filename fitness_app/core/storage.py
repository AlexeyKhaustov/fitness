# fitness_app/core/storage.py
"""
Абстракция хранилища для видеофайлов.
Поддерживает локальное хранилище, generic S3 и Cloud.ru S3.
"""

import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings
from django.core.files.storage import Storage
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)


class VideoStorageInterface(ABC):
    """Интерфейс для низкоуровневых операций с файлами (используется в задачах)"""
    @abstractmethod
    def save_file(self, local_path: str, remote_path: str) -> str:
        pass

    @abstractmethod
    def load_file(self, remote_path: str, local_path: str) -> None:
        pass

    @abstractmethod
    def get_signed_url(self, remote_path: str, expires: int = settings.AWS_QUERYSTRING_EXPIRE) -> str:
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        pass


class LocalVideoStorage(VideoStorageInterface):
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.path.join(settings.MEDIA_ROOT, "videos")
        logger.info(f"LocalVideoStorage инициализирован с base_path={self.base_path}")

    def save_file(self, local_path: str, remote_path: str) -> str:
        dest = os.path.join(self.base_path, remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)
        url = settings.MEDIA_URL + "videos/" + remote_path
        logger.debug(f"Файл скопирован: {local_path} -> {dest}, URL={url}")
        return url

    def load_file(self, remote_path: str, local_path: str) -> None:
        src = os.path.join(self.base_path, remote_path)
        shutil.copy2(src, local_path)
        logger.debug(f"Файл загружен: {src} -> {local_path}")

    def get_signed_url(self, remote_path: str, expires: int = settings.AWS_QUERYSTRING_EXPIRE) -> str:
        return f"videos/{remote_path}"

    def delete_file(self, remote_path: str) -> None:
        path = os.path.join(self.base_path, remote_path)
        if os.path.exists(path):
            os.remove(path)
            logger.debug(f"Удалён файл: {path}")
        else:
            logger.warning(f"Файл не найден для удаления: {path}")

    # Методы для совместимости с Django Storage API
    def save(self, name, content, max_length=None):
        return name

    def url(self, name):
        return self.get_signed_url(name)


class GenericS3VideoStorage(VideoStorageInterface):
    """Универсальное S3-хранилище, оборачивает S3Boto3Storage"""
    def __init__(self, **options):
        if not options:
            options = settings.STORAGES['private_video']['OPTIONS']
        self.storage = S3Boto3Storage(
            bucket_name=options['bucket_name'],
            endpoint_url=options['endpoint_url'],
            region_name=options['region_name'],
            access_key=options['access_key'],
            secret_key=options['secret_key'],
            default_acl=options.get('default_acl', 'private'),
            querystring_auth=options.get('querystring_auth', True),
        )
        logger.info("GenericS3VideoStorage инициализирован")

    def save_file(self, local_path: str, remote_path: str) -> str:
        with open(local_path, "rb") as f:
            self.storage.save(remote_path, f)
        url = self.storage.url(remote_path)
        logger.debug(f"Файл загружен в S3: {local_path} -> {remote_path}, URL={url}")
        return url

    def load_file(self, remote_path: str, local_path: str) -> None:
        with self.storage.open(remote_path, "rb") as f:
            content = f.read()
        with open(local_path, "wb") as f:
            f.write(content)
        logger.debug(f"Файл загружен из S3: {remote_path} -> {local_path}")

    def get_signed_url(self, remote_path: str, expires: int = settings.AWS_QUERYSTRING_EXPIRE) -> str:
        return self.storage.url(remote_path, expire=expires)

    def delete_file(self, remote_path: str) -> None:
        self.storage.delete(remote_path)
        logger.debug(f"Удалён файл из S3: {remote_path}")

    # Методы для Django Storage API
    def save(self, name, content, max_length=None):
        return self.storage.save(name, content, max_length)

    def url(self, name):
        return self.storage.url(name)

    def open(self, name, mode='rb'):
        return self.storage.open(name, mode)

    def exists(self, name):
        return self.storage.exists(name)

    def delete(self, name):
        self.storage.delete(name)

    def size(self, name):
        return self.storage.size(name)

    def get_available_name(self, name, max_length=None):
        return self.storage.get_available_name(name, max_length)

    def generate_filename(self, filename):
        return self.storage.generate_filename(filename)


class CloudRuS3VideoStorage(Storage, VideoStorageInterface):
    """
    Специализированное хранилище для Cloud.ru Object Storage.
    Наследуется от Django Storage для полной совместимости.
    """
    def __init__(self, **options):
        if not options:
            options = settings.STORAGES['private_video']['OPTIONS']
        self.bucket_name = options['bucket_name']
        self.endpoint_url = options['endpoint_url']
        self.region_name = options['region_name']
        self.access_key = options['access_key']
        self.secret_key = options['secret_key']
        self.default_acl = options.get('default_acl', 'private')
        self.querystring_expire = options.get('querystring_expire', settings.AWS_QUERYSTRING_EXPIRE)
        # location не используем, т.к. upload_to сам формирует путь
        self.location = ''

        # Клиент для подписанных URL (path-style)
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(
                s3={'addressing_style': 'path'},
                signature_version='s3v4',
            )
        )

        # Внутреннее хранилище для операций (без подписей)
        self._storage = S3Boto3Storage(
            bucket_name=self.bucket_name,
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            access_key=self.access_key,
            secret_key=self.secret_key,
            default_acl=self.default_acl,
            querystring_auth=False,
        )
        logger.info(f"CloudRuS3VideoStorage инициализирован для бакета {self.bucket_name}")

    def _normalize_name(self, name):
        """Не добавляем location, так как upload_to уже формирует полный путь"""
        return name

    # --- Методы VideoStorageInterface (для задач) ---
    def save_file(self, local_path: str, remote_path: str) -> str:
        with open(local_path, 'rb') as f:
            self._storage.save(remote_path, f)
        url = self.get_signed_url(remote_path, expires=self.querystring_expire)
        logger.debug(f"Файл загружен в Cloud.ru S3: {local_path} -> {remote_path}, URL={url}")
        return url

    def load_file(self, remote_path: str, local_path: str) -> None:
        with self._storage.open(remote_path, 'rb') as f:
            content = f.read()
        with open(local_path, 'wb') as f:
            f.write(content)
        logger.debug(f"Файл загружен из Cloud.ru S3: {remote_path} -> {local_path}")

    def get_signed_url(self, remote_path: str, expires: int = settings.AWS_QUERYSTRING_EXPIRE) -> str:
        expires = expires or self.querystring_expire
        url = self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket_name, 'Key': remote_path},
            ExpiresIn=expires,
            HttpMethod='GET'
        )
        logger.debug(f"Сгенерирован подписанный URL для {remote_path}, expires={expires}")
        return url

    def delete_file(self, remote_path: str) -> None:
        self._storage.delete(remote_path)
        logger.debug(f"Удалён файл из Cloud.ru S3: {remote_path}")

    # --- Методы Django Storage API ---
    def _save(self, name, content):
        """Django вызывает этот метод для сохранения файла из UploadedFile"""
        return self._storage._save(name, content)

    def _open(self, name, mode='rb'):
        return self._storage._open(name, mode)

    def url(self, name):
        return self.get_signed_url(name, expires=self.querystring_expire)

    def exists(self, name):
        return self._storage.exists(name)

    def delete(self, name):
        self._storage.delete(name)

    def size(self, name):
        return self._storage.size(name)

    def get_available_name(self, name, max_length=None):
        return self._storage.get_available_name(name, max_length)

    def generate_filename(self, filename):
        return self._storage.generate_filename(filename)

    def save(self, name, content, max_length=None):
        return self._save(name, content)


def get_video_storage() -> VideoStorageInterface:
    """
    Фабрика, возвращающая реализацию VideoStorageInterface для задач.
    """
    use_s3 = getattr(settings, "USE_S3", False)
    if not use_s3:
        logger.info("Выбран LocalVideoStorage")
        return LocalVideoStorage()

    s3_provider = getattr(settings, "S3_PROVIDER", "generic").lower()
    if s3_provider == "cloudru":
        logger.info("Выбран CloudRuS3VideoStorage (Cloud.ru)")
        return CloudRuS3VideoStorage()
    else:
        logger.info(f"Выбран GenericS3VideoStorage (провайдер: {s3_provider})")
        return GenericS3VideoStorage()