import os
from mimetypes import guess_type
from anyio import Path
import aioboto3
from contextlib import asynccontextmanager

from typing import List, Optional, Any

import logging
import requests
from pathlib import Path as SyncPath
from tempfile import TemporaryFile

from urllib.parse import urlparse

from openpuc_scrapers.models.constants import (
    LOCAL_CACHE_DIR,
    OPENSCRAPERS_S3_CLOUD_REGION,
    OPENSCRAPERS_S3_SECRET_KEY,
    OPENSCRAPERS_S3_ACCESS_KEY,
    OPENSCRAPERS_S3_ENDPOINT,
    TMP_DIR,
)

from typing import Any, Optional
import base64
import secrets

import logging
import shutil

default_logger = logging.getLogger(__name__)


def rand_string() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(8)).decode()


def rand_filepath() -> SyncPath:
    return SyncPath(rand_string())


class S3FileManager:
    def __init__(self, bucket: str) -> None:
        self.endpoint = OPENSCRAPERS_S3_ENDPOINT

        if not all([OPENSCRAPERS_S3_ACCESS_KEY, OPENSCRAPERS_S3_SECRET_KEY]):
            raise ValueError("Missing S3 credentials in environment variables")
        if not OPENSCRAPERS_S3_ENDPOINT:
            raise ValueError("Missing S3 endpoint configuration")

        self.tmpdir = TMP_DIR
        self.bucket = bucket
        self._session = aioboto3.Session(
            aws_access_key_id=OPENSCRAPERS_S3_ACCESS_KEY,
            aws_secret_access_key=OPENSCRAPERS_S3_SECRET_KEY,
            region_name=OPENSCRAPERS_S3_CLOUD_REGION,
        )
        if LOCAL_CACHE_DIR is not None:
            self.s3_cache_directory = LOCAL_CACHE_DIR / SyncPath(self.bucket)
        else:
            self.s3_cache_directory = (
                TMP_DIR / SyncPath("s3_cache") / SyncPath(self.bucket)
            )

    def get_local_dir_from_key(self, key: str) -> SyncPath:
        return self.s3_cache_directory / SyncPath(key)

    @asynccontextmanager
    async def _get_client(self):
        async with self._session.client("s3", endpoint_url=self.endpoint) as client:
            yield client

    async def save_string_to_remote_file_async(self, key: str, content: str) -> None:
        if not content:
            default_logger.error(f"Tried to upload to {key} with empty content")
            return

        local_path = self.get_local_dir_from_key(key)
        await local_path.parent.mkdir(parents=True, exist_ok=True)
        await local_path.write_text(content, encoding="utf-8")
        await self.push_file_to_s3_async(local_path, key)

    async def download_s3_file_to_path_async(
        self, file_name: str, bucket: Optional[str] = None, serve_cache: bool = False
    ) -> Optional[SyncPath]:
        file_path = self.get_local_dir_from_key(file_name)
        if bucket is None:
            bucket = self.bucket
        if file_path.is_file():
            if serve_cache:
                return file_path
            file_path.unlink()
        async with self._get_client() as s3:
            await s3.download_file(bucket or self.bucket, file_name, str(file_path))
        return file_path

    async def download_s3_file_to_string_async(
        self, file_name: str, bucket: Optional[str] = None, serve_cache: bool = False
    ) -> str:
        path = await self.download_s3_file_to_path_async(
            file_name, bucket, serve_cache=serve_cache
        )
        if path is None:
            raise ValueError("Error Encountered getting file from s3.")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    async def download_file_from_s3_url(self, s3_url: str) -> Optional[SyncPath]:
        url_parsed = urlparse(s3_url)
        domain = url_parsed.hostname
        s3_key = url_parsed.path
        if domain is None or s3_key is None:
            raise ValueError("Invalid URL")
        s3_bucket = domain.split(".")[0]
        return await self.download_s3_file_to_path_async(
            file_name=s3_key, bucket=s3_bucket
        )

    def generate_s3_uri(
        self,
        file_name: str,
        bucket: Optional[str] = None,
        s3_endpoint: Optional[str] = None,
    ) -> str:
        if s3_endpoint is None:
            s3_endpoint = self.endpoint

        if bucket is None:
            bucket = self.bucket

        s3_endpoint = s3_endpoint.rstrip("/")
        base_endpoint = s3_endpoint.split("//")[-1]
        s3_uri = f"https://{bucket}.{base_endpoint}/{file_name}"
        return s3_uri

    async def push_file_to_s3_async(
        self,
        filepath: Path,
        file_upload_key: str,
        bucket: Optional[str] = None,
        immutable: bool = False,
    ) -> str:
        mutable = not immutable
        if bucket is None:
            bucket = self.bucket
        local_cache_filepath = self.get_local_dir_from_key(file_upload_key)
        if mutable or not local_cache_filepath.exists():
            if filepath != local_cache_filepath:
                try:
                    if not await filepath.exists():
                        raise FileNotFoundError(
                            f"Source file {filepath} does not exist"
                        )
                    await local_cache_filepath.parent.mkdir(parents=True, exist_ok=True)
                    default_logger.info(f"Copying {filepath} to {local_cache_filepath}")
                except Exception as e:
                    default_logger.warning(
                        f"Encountered error copying file to cache: {e}"
                    )
                    raise e
        if mutable or not self.does_file_exist_s3(key=file_upload_key, bucket=bucket):
            if not await filepath.exists():
                raise FileNotFoundError(f"Source file {filepath} does not exist")
            default_logger.info(
                f"Uploading file {filepath}, to s3 key: {file_upload_key}"
            )
        try:

            content_type = guess_type(file_upload_key)[0] or "application/octet-stream"
            if file_upload_key.endswith(".json"):
                content_type = "application/json"

            default_logger.debug(
                f"Uploading {filepath} (Size: {await filepath.stat().st_size} bytes) with Content-Type: {content_type}"
            )

            async with self._get_client() as s3:
                await s3.upload_file(
                    str(filepath),
                    bucket or self.bucket,
                    file_upload_key,
                    ExtraArgs={
                        "ContentType": content_type,
                        "Metadata": {
                            "source-file": str(filepath.name),
                            "upload-system": "open-scrapers",
                        },
                    },
                )
            return file_upload_key
        except Exception as e:
            default_logger.error(f"Failed to upload {file_upload_key} from {filepath}")
            default_logger.error(
                f"File exists: {await filepath.exists()}, size: {await filepath.stat().st_size if await filepath.exists() else 0}"
            )
            default_logger.error(f"Bucket: {bucket}, Key: {file_upload_key}")
            return file_upload_key

    async def list_objects_with_prefix_async(self, prefix: str) -> List[str]:
        async with self._get_client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            keys = []
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                keys.extend([obj["Key"] for obj in page.get("Contents", [])])
            return keys
