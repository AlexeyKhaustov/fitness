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

    def url(self, name: str, expire: Optional[int] = None) -> str:
        """Алиас для get_url с signed=False (локальное хранилище)"""
        return self.get_url(name, signed=False, expires=expire or 3600)

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

    def url(self, name: str, expire: Optional[int] = None) -> str:
        """Алиас для get_url с signed=True и expire из настроек или переданного значения"""
        expire = expire or getattr(self.storage, 'querystring_expire', 3600)
        return self.get_url(name, signed=True, expires=expire)

    def delete(self, remote_path: str) -> None:
        self.storage.delete(remote_path)
        logger.debug(f"Удалён файл из S3: {remote_path}")


class CloudRuS3VideoStorage(VideoStorageInterface):
    """
    Специализированное хранилище для Cloud.ru Object Storage.
    Принимает **options для совместимости с STORAGES.
    Учитывает path-style addressing и tenant_id в access_key.
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
        self.querystring_expire = options.get('querystring_expire', 3600)

        # Создаём низкоуровневый клиент boto3 с правильной конфигурацией
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
        logger.info(f"CloudRuS3VideoStorage инициализирован для бакета {self.bucket_name}")

    def save(self, local_path: str, remote_path: str) -> str:
        extra_args = {'ACL': self.default_acl} if self.default_acl else {}
        with open(local_path, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=remote_path,
                Body=f,
                **extra_args
            )
        url = self.get_url(remote_path, signed=True, expires=self.querystring_expire)
        logger.debug(f"Файл загружен в Cloud.ru S3: {local_path} -> {remote_path}, URL={url}")
        return url

    def load(self, remote_path: str, local_path: str) -> None:
        response = self.client.get_object(Bucket=self.bucket_name, Key=remote_path)
        with open(local_path, 'wb') as f:
            f.write(response['Body'].read())
        logger.debug(f"Файл загружен из Cloud.ru S3: {remote_path} -> {local_path}")

    def get_url(self, remote_path: str, signed: bool = True, expires: int = 3600) -> str:
        if not signed:
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

    def url(self, name: str, expire: Optional[int] = None) -> str:
        """Алиас для get_url с signed=True и expire из настроек или переданного значения"""
        expire = expire or self.querystring_expire
        return self.get_url(name, signed=True, expires=expire)

    def delete(self, remote_path: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=remote_path)
        logger.debug(f"Удалён файл из Cloud.ru S3: {remote_path}")


def get_video_storage() -> VideoStorageInterface:
    """
    Фабрика, возвращающая нужную реализацию хранилища.
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