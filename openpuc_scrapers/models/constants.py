import os
from pathlib import Path
from typing import Callable

from typing import Optional


def Maybe(f: Callable) -> Callable:
    return lambda x: f(x) if x is not None else None


OPENSCRAPERS_S3_CLOUD_REGION = os.environ.get("OPENSCRAPERS_S3_CLOUD_REGION", "sfo3")
OPENSCRAPERS_S3_ENDPOINT = os.environ.get(
    "OPENSCRAPERS_S3_ENDPOINT", "https://sfo3.digitaloceanspaces.com"
)
# OPENSCRAPERS_S3_SCRAPER_INTERMEDIATE_BUCKET = os.environ.get(
#     "OPENSCRAPERS_S3_SCRAPER_INTERMEDIATE_BUCKET", "opescraper-intermediates"
# )

OPENSCRAPERS_S3_OBJECT_BUCKET = os.environ.get(
    "OPENSCRAPERS_S3_OBJECT_BUCKET", "opescrapers"
)

OPENSCRAPERS_SQL_DB_SCONNECTION = os.environ.get(
    "OPENSCRAPERS_SQL_DB_SCONNECTION", "sqlite+aiosqlite:///db.sqlite3"
)


TMP_DIR = Path(os.environ.get("TMP_DIR", "/tmp/open_scrapers"))


LOCAL_CACHE_DIR: Optional[Path] = (
    None
    if os.environ.get("LOCAL_CACHE_DIR") is None
    else Path(os.environ.get("LOCAL_CACHE_DIR"))
)

OPENSCRAPERS_S3_ACCESS_KEY = os.environ["OPENSCRAPERS_S3_ACCESS_KEY"]
OPENSCRAPERS_S3_SECRET_KEY = os.environ["OPENSCRAPERS_S3_SECRET_KEY"]
