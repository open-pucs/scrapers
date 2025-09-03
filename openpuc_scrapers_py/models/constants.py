import os
from pathlib import Path
from typing import Callable

from typing import Optional


def Maybe(f: Callable) -> Callable:
    return lambda x: f(x) if x is not None else None


DEEPINFRA_API_KEY = os.environ["DEEPINFRA_API_KEY"]

DEFAULT_OPENSCRAPERS_SQL_CONNECTION = (
    "postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow"
)

# DEFAULT_OPENSCRAPERS_SQL_CONNECTION = "sqlite+aiosqlite:///db.sqlite3"
OPENSCRAPERS_SQL_DB_CONNECTION = os.environ.get(
    "OPENSCRAPERS_SQL_DB_CONNECTION", DEFAULT_OPENSCRAPERS_SQL_CONNECTION
)


TMP_DIR = Path(os.environ.get("TMP_DIR", "/tmp/open_scrapers"))


LOCAL_CACHE_DIR: Optional[Path] = (
    None
    if os.environ.get("LOCAL_CACHE_DIR") is None
    else Path(os.environ.get("LOCAL_CACHE_DIR"))
)


OPENSCRAPERS_INTERNAL_API_URL = (
    os.environ.get("OPENSCRAPERS_INTERNAL_API_URL") or "http://localhost:33399"
)
