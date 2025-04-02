import json
from pathlib import Path
from typing import Any, List
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.networking import (
    post_list_to_endpoint_split,
)


from openpuc_scrapers.pipelines.s3_utils import S3FileManager
from openpuc_scrapers.scrapers.base import (
    GenericScraper,
    StateCaseData,
    StateFilingData,
)


# Helper functions
def save_to_disk_and_s3(path: str, content: str) -> None:
    S3FileManager().save_string_to_remote_file(path, content)


# isnt working due to the higher order types sadly
# def save_json(path: str, data: BaseModel | List[BaseModel]) -> None:
def save_json(path: str, data: Any) -> None:
    if isinstance(data, dict):
        json_data = data
    if isinstance(data, BaseModel):
        json_data = data.model_dump()
    if isinstance(data, list):
        json_data = [item.model_dump() for item in data]
    else:
        raise Exception("Data is not a list, dict, or BaseModel")
    json_str = json.dumps(json_data, indent=2)
    save_to_disk_and_s3(path, json_str)


# Processing functions
def process_cases(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    cases: List[StateCaseData],
    base_path: str,
) -> List[GenericCase]:
    all_generic_cases = []

    for case in cases:
        generic_case = scraper.into_generic_case_data(case)
        case_num = generic_case.case_number

        # Save state-specific case data
        case_path = f"{base_path}/cases/case_{case_num}.json"
        save_json(case_path, case)

        # Process filings
        filings_intermediate = scraper.filing_data_intermediate(case)
        filings_path = f"{base_path}/filings/case_{case_num}.json"
        save_json(filings_path, filings_intermediate)

        filings = scraper.filing_data_from_intermediate(filings_intermediate)
        filings_json_path = f"{base_path}/filings/case_{case_num}.json"
        save_json(filings_json_path, filings)

        # Convert to generic case
        generic_case = scraper.into_generic_filing_data

        case_specific_generic_cases = []
        for filing in filings:
            generic_filing = scraper.into_generic_filing_data(filing)
            case_specific_generic_cases.append(generic_filing)
        all_generic_cases.extend(case_specific_generic_cases)

    return all_generic_cases


def get_all_cases(
    scraper: GenericScraper[StateCaseData, StateFilingData]
) -> List[GenericCase]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_path = f"data/{timestamp}"

    # Get and save case list
    caselist_intermediate = scraper.universal_caselist_intermediate()
    caselist_path = f"{base_path}/caselist.json"
    save_json(caselist_path, caselist_intermediate)

    # Process cases
    state_cases = scraper.universal_caselist_from_intermediate(caselist_intermediate)
    return process_cases(scraper, state_cases, base_path)


def get_new_cases_since_date(
    scraper: GenericScraper[StateCaseData, StateFilingData], after_date: date
) -> List[GenericCase]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_path = f"data/{timestamp}"

    # Get and save updated cases
    updated_intermediate = scraper.updated_cases_since_date_intermediate(after_date)
    updated_path = f"{base_path}/updated_cases.json"
    save_json(updated_path, updated_intermediate)

    # Process updated cases
    state_cases = scraper.updated_cases_since_date_from_intermediate(
        updated_intermediate, after_date
    )
    return process_cases(scraper, state_cases, base_path)


async def scrape_and_send_cases_to_endpoint(
    scraper: GenericScraper,
    post_endpoint: str,
    max_request_size: int = 1000,
    max_simul_requests: int = 10,
) -> List[dict]:
    cases = get_all_cases(scraper)

    return await post_list_to_endpoint_split(
        objects=cases,
        post_endpoint=post_endpoint,
        max_simul_requests=max_simul_requests,
        max_request_size=max_request_size,
    )
