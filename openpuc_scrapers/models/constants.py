import os
from pathlib import Path
from typing import Callable

from typing import Optional


def Maybe(f: Callable) -> Callable:
    return lambda x: f(x) if x is not None else None


S3_CLOUD_REGION = os.environ.get("S3_CLOUD_REGION", "sfo3")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "https://sfo3.digitaloceanspaces.com")
S3_SCRAPER_INTERMEDIATE_BUCKET = os.environ.get(
    "S3_SCRAPER_INTERMEDIATE_BUCKET", "opescraper-intermediates"
)


TMP_DIR = Path(os.environ.get("TMP_DIR", "/tmp/open_scrapers"))


LOCAL_CACHE_DIR: Optional[Path] = Maybe(Path)(os.environ.get("LOCAL_CACHE_DIR"))

S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
