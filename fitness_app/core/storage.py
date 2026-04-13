# fitness_app/core/storage.py
"""
Абстракция хранилища для видеофайлов.
Поддерживает локальное хранилище и S3 (общий случай + Cloud.ru).
"""

import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)


class VideoStorageInterface(ABC):
    @abstractmethod
    def save(self, local_path: str, remote_path: str) -> str:
        pass

    @abstractmethod
    def load(self, remote_path: str, local_path: str) -> None:
        pass

    @abstractmethod
    def get_url(self, remote_path: str, signed: bool = False, expires: int = 3600) -> str:
        pass

    @abstractmethod
    def delete(self, remote_path: str) -> None:
        pass


class LocalVideoStorage(VideoStorageInterface):
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
        return f"videos/{remote_path}"

    def delete(self, remote_path: str) -> None:
        path = os.path.join(self.base_path, remote_path)
        if os.path.exists(path):
            os.remove(path)
            logger.debug(f"Удалён файл: {path}")
        else:
            logger.warning(f"Файл не найден для удаления: {path}")


class GenericS3VideoStorage(VideoStorageInterface):
    """
    Универсальное S3-хранилище (для AWS, Selectel, VK Cloud и т.п.),
    использует стандартный S3Boto3Storage.
    """
    def __init__(self):
        opts = settings.STORAGES['private_video']['OPTIONS']
        self.storage = S3Boto3Storage(
            bucket_name=opts['bucket_name'],
            endpoint_url=opts['endpoint_url'],
            region_name=opts['region_name'],
            access_key=opts['access_key'],
            secret_key=opts['secret_key'],
            default_acl=opts.get('default_acl', 'private'),
            querystring_auth=opts.get('querystring_auth', True),
        )
        logger.info("GenericS3VideoStorage инициализирован из настроек STORAGES")

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
            url = self.storage.url(remote_path)
        logger.debug(f"Сгенерирован URL для {remote_path}, signed={signed}, expires={expires}")
        return url

    def delete(self, remote_path: str) -> None:
        self.storage.delete(remote_path)
        logger.debug(f"Удалён файл из S3: {remote_path}")


class CloudRuS3VideoStorage(VideoStorageInterface):
    """
    Специализированное хранилище для Cloud.ru Object Storage.
    Учитывает:
    - path-style addressing (обязательно)
    - tenant_id в access_key (формат tenant:key)
    - корректную генерацию подписанных URL через boto3 напрямую
    """
    def __init__(self):
        opts = settings.STORAGES['private_video']['OPTIONS']
        self.bucket_name = opts['bucket_name']
        self.endpoint_url = opts['endpoint_url']
        self.region_name = opts['region_name']
        self.access_key = opts['access_key']          # уже в формате tenant:key
        self.secret_key = opts['secret_key']
        self.default_acl = opts.get('default_acl', 'private')
        self.querystring_expire = opts.get('querystring_expire', 3600)

        # Создаём низкоуровневый клиент boto3 с правильной конфигурацией
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(
                s3={'addressing_style': 'path'},      # Cloud.ru требует path-style
                signature_version='s3v4',
            )
        )
        logger.info(f"CloudRuS3VideoStorage инициализирован для бакета {self.bucket_name}")

    def save(self, local_path: str, remote_path: str) -> str:
        """Загружает файл в бакет, устанавливая ACL private (по умолчанию)."""
        extra_args = {'ACL': self.default_acl} if self.default_acl else {}
        with open(local_path, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=remote_path,
                Body=f,
                **extra_args
            )
        # Возвращаем подписанный URL (можно и без подписи, но для единообразия)
        url = self.get_url(remote_path, signed=True, expires=self.querystring_expire)
        logger.debug(f"Файл загружен в Cloud.ru S3: {local_path} -> {remote_path}, URL={url}")
        return url

    def load(self, remote_path: str, local_path: str) -> None:
        """Скачивает файл из бакета во временную папку."""
        response = self.client.get_object(Bucket=self.bucket_name, Key=remote_path)
        with open(local_path, 'wb') as f:
            f.write(response['Body'].read())
        logger.debug(f"Файл загружен из Cloud.ru S3: {remote_path} -> {local_path}")

    def get_url(self, remote_path: str, signed: bool = True, expires: int = 3600) -> str:
        """
        Генерирует подписанный URL для доступа к объекту.
        Если signed=False — возвращает публичную ссылку (но объект приватный, так что не будет работать).
        Для Cloud.ru всегда используем signed=True.
        """
        if not signed:
            # Публичная ссылка (если объект public-read, но у нас private)
            return f"{self.endpoint_url}/{self.bucket_name}/{remote_path}"

        expires = expires or self.querystring_expire
        url = self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket_name, 'Key': remote_path},
            ExpiresIn=expires,
            HttpMethod='GET'
        )
        logger.debug(f"Сгенерирован подписанный URL для {remote_path}, expires={expires}")
        return url

    def delete(self, remote_path: str) -> None:
        """Удаляет объект из бакета."""
        self.client.delete_object(Bucket=self.bucket_name, Key=remote_path)
        logger.debug(f"Удалён файл из Cloud.ru S3: {remote_path}")


def get_video_storage() -> VideoStorageInterface:
    """
    Фабрика, возвращающая нужную реализацию хранилища.
    Логика:
    - Если USE_S3=False -> LocalVideoStorage
    - Если USE_S3=True:
        - Если S3_PROVIDER='cloudru' -> CloudRuS3VideoStorage
        - Иначе -> GenericS3VideoStorage (для обратной совместимости)
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