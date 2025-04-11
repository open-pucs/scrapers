from datetime import datetime
from typing import Any, List
from pydantic import BaseModel
from dateutil.parser import parse
from openpuc_scrapers.db.s3_utils import push_case_to_s3_and_db
from openpuc_scrapers.models.constants import S3_SCRAPER_INTERMEDIATE_BUCKET
from openpuc_scrapers.models.case import (
    GenericCase,
    GenericFiling,
)
from openpuc_scrapers.scrapers.base import (
    GenericScraper,
    StateCaseData,
    StateFilingData,
)


def generate_intermediate_object_save_path(state: str, jurisdiction_name: str) -> str:
    time_now = datetime.now().isoformat()
    return f"{state}/{jurisdiction_name}/{time_now}"


def get_scraper_unvalidated(state: str, jurisdiction_name: str) -> GenericScraper:
    # Implement your scraper instantiation logic here
    return GenericScraper(state=state, jurisdiction_name=jurisdiction_name)
