import flytekit as fl

from typing import Any, List
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase


from openpuc_scrapers.models.timestamp import rfc_time_now
from openpuc_scrapers.pipelines.helper_utils import save_json
from openpuc_scrapers.scrapers.base import (
    GenericScraper,
    StateCaseData,
    StateFilingData,
)


def generate_intermediate_object_save_path(
    scraper: GenericScraper[StateCaseData, StateFilingData]
):
    time_now = rfc_time_now()
    base_path = f"{scraper.state}/{scraper.jurisdiction_name}/{str(time_now)}"

    return base_path


@fl.workflow
def get_all_cases_complete(
    scraper: GenericScraper[StateCaseData, StateFilingData]
) -> List[GenericCase]:
    caselist = get_all_caselist_raw(scraper)
    return fl.map(process_case)(caselist)


@fl.workflow
def get_new_cases_since_date_complete(
    scraper: GenericScraper[StateCaseData, StateFilingData], after_date: date
) -> List[GenericCase]:
    caselist = get_new_cases_since_date_complete(scraper=scraper, after_date=after_date)
    return fl.map(process_case)(caselist)


@fl.task
def process_case(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: StateCaseData,
    base_path: str,
) -> GenericCase:
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

    case_specific_generic_cases = []
    for filing in filings:
        generic_filing = scraper.into_generic_filing_data(filing)
        case_specific_generic_cases.append(generic_filing)

    generic_case.filings = case_specific_generic_cases
    return generic_case


@fl.task
def get_all_caselist_raw(
    scraper: GenericScraper[StateCaseData, StateFilingData], base_path: str
) -> List[StateCaseData]:
    # Get and save case list
    caselist_intermediate = scraper.universal_caselist_intermediate()
    caselist_path = f"{base_path}/caselist.json"
    save_json(caselist_path, caselist_intermediate)

    # Process cases
    state_cases = scraper.universal_caselist_from_intermediate(caselist_intermediate)
    return state_cases


@fl.task
def get_new_caselist_since_date(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    after_date: date,
    base_path: str,
) -> List[StateCaseData]:
    # Get and save updated cases
    updated_intermediate = scraper.updated_cases_since_date_intermediate(after_date)
    updated_path = f"{base_path}/updated_cases.json"
    save_json(updated_path, updated_intermediate)

    # Process updated cases
    state_cases = scraper.updated_cases_since_date_from_intermediate(
        updated_intermediate, after_date
    )
    return state_cases
