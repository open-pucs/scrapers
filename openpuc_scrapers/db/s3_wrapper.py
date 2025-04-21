import os
import boto3


from typing import Optional, Any

import logging
import requests
from pathlib import Path
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


def rand_filepath() -> Path:
    return Path(rand_string())


""""
All of the functions here are synchronous, both due to the fact that boto3 is sync, and also most file operations in linux are synchronous, in order to use async operations on these go ahead and use 

await asyncio.to_thread(<sync s3 function>)
"""


class S3FileManager:
    def __init__(self, bucket: str) -> None:
        self.endpoint = OPENSCRAPERS_S3_ENDPOINT
        self.logger = default_logger

        self.tmpdir = TMP_DIR

        # Create directories if they don't exist

        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=OPENSCRAPERS_S3_ACCESS_KEY,
            aws_secret_access_key=OPENSCRAPERS_S3_SECRET_KEY,
            region_name=OPENSCRAPERS_S3_CLOUD_REGION,
        )
        self.bucket = bucket
        if LOCAL_CACHE_DIR is not None:
            self.s3_cache_directory = LOCAL_CACHE_DIR / Path(self.bucket)
        else:
            self.s3_cache_directory = TMP_DIR / Path("s3_cache") / Path(self.bucket)

    def get_local_dir_from_key(self, key: str) -> Path:
        return self.s3_cache_directory / Path(key)

    def save_string_to_remote_file(self, key: str, content: str):
        local_path = self.get_local_dir_from_key(key)
        if local_path is None:
            local_path = self.tmpdir / rand_filepath()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")
        self.push_file_to_s3(local_path, key)

    def download_file_to_path(self, url: str, savepath: Path) -> Path:
        savepath.parent.mkdir(exist_ok=True, parents=True)
        self.logger.info(f"Downloading file to dir: {savepath}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(savepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
        return savepath

    # TODO : Get types for temporary file
    def download_file_to_tmpfile(self, url: str) -> Any:
        self.logger.info(f"Downloading file to temporary file")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with TemporaryFile("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
                return f

    # S3 Stuff Below this point

    def download_s3_file_to_path(
        self, file_name: str, bucket: Optional[str] = None, serve_cache: bool = False
    ) -> Optional[Path]:
        file_path = self.get_local_dir_from_key(file_name)
        if bucket is None:
            bucket = self.bucket
        if file_path.is_file():
            if serve_cache:
                return file_path
            os.remove(file_path)
            # raise Exception("File Already Present at Path, not downloading")
        try:
            self.s3.download_file(bucket, file_name, str(file_path))
            return file_path
        except Exception as e:
            self.logger.error(
                f"Something whent wrong when downloading s3, is the file missing, raised error {e}"
            )
            return None

    def download_s3_file_to_string(
        self, file_name: str, bucket: Optional[str] = None, serve_cache: bool = False
    ) -> str:
        path = self.download_s3_file_to_path(file_name, bucket, serve_cache=serve_cache)
        if path is None:
            raise ValueError("Error Encountered getting file from s3.")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def download_file_from_s3_url(self, s3_url: str) -> Optional[Path]:
        url_parsed = urlparse(s3_url)
        domain = url_parsed.hostname
        s3_key = url_parsed.path
        if domain is None or s3_key is None:
            raise ValueError("Invalid URL")
        s3_bucket = domain.split(".")[0]
        return self.download_s3_file_to_path(file_name=s3_key, bucket=s3_bucket)

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

        # Remove any trailing slashes from the S3 endpoint
        s3_endpoint = s3_endpoint.rstrip("/")

        # Extract the base endpoint (e.g., sfo3.digitaloceanspaces.com)
        base_endpoint = s3_endpoint.split("//")[-1]

        # Construct the S3 URI
        s3_uri = f"https://{bucket}.{base_endpoint}/{file_name}"

        return s3_uri

    def does_file_exist_s3(self, key: str, bucket: Optional[str] = None) -> bool:
        if bucket is None:
            bucket = self.bucket

        try:
            self.s3.get_object(
                Bucket=bucket,
                Key=key,
            )
            return True
        except self.s3.exceptions.NoSuchKey:
            return False

    def download_file_to_file_in_tmpdir(
        self, url: str
    ) -> Any:  # TODO : Get types for temporary file
        savedir = self.tmpdir / Path(rand_string())
        return self.download_file_to_path(url, savedir)

    def push_file_to_s3(
        self, filepath: Path, file_upload_key: str, bucket: Optional[str] = None
    ) -> str:
        if bucket is None:
            bucket = self.bucket
        local_cache_filepath = self.get_local_dir_from_key(file_upload_key)
        if filepath != local_cache_filepath:
            try:
                shutil.copyfile(filepath, local_cache_filepath)
            except Exception as e:
                default_logger.warning(f"Encountered error copying file to cache: {e}")
        return self.s3.upload_file(str(filepath), bucket, file_upload_key)
