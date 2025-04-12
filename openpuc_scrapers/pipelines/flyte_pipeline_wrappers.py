import flytekit as fl

from typing import Any, List
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.db.s3_utils import push_case_to_s3_and_db
from openpuc_scrapers.models.constants import S3_SCRAPER_INTERMEDIATE_BUCKET
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase


from openpuc_scrapers.models.timestamp import rfc_time_now
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw,
    get_new_caselist_since_date,
    process_case,
)
from openpuc_scrapers.pipelines.helper_utils import save_json
from openpuc_scrapers.pipelines.raw_attachment_handling import process_generic_filing
from openpuc_scrapers.scrapers.base import (
    GenericScraper,
    StateCaseData,
    StateFilingData,
)


@fl.workflow
def get_all_cases_complete(
    scraper: GenericScraper[StateCaseData, StateFilingData]
) -> List[GenericCase]:
    base_path = generate_intermediate_object_save_path(scraper)
    caselist = get_all_caselist_raw(scraper, base_path=base_path)
    return fl.map(process_case)(caselist)


@fl.workflow
def get_new_cases_since_date_complete_flyte(
    scraper: GenericScraper[StateCaseData, StateFilingData], after_date: date
) -> List[GenericCase]:
    base_path = generate_intermediate_object_save_path(scraper)
    caselist = get_new_caselist_since_date(
        scraper=scraper, after_date=after_date, base_path=base_path
    )
    return fl.map(process_case)(caselist)


@fl.task
def process_case_flyte(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: StateCaseData,
    base_path: str,
) -> GenericCase:
    return process_case(scraper=scraper, case=case, base_path=base_path)


@fl.task
def get_all_caselist_raw_flyte(
    scraper: GenericScraper[StateCaseData, StateFilingData], base_path: str
) -> List[StateCaseData]:
    return get_all_caselist_raw(scraper=scraper, base_path=base_path)


@fl.task
def get_new_caselist_since_date_flyte(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    after_date: date,
    base_path: str,
) -> List[StateCaseData]:
    return get_new_caselist_since_date(
        scraper=scraper, after_date=after_date, base_path=base_path
    )
