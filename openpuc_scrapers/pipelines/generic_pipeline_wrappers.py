import logging
import traceback
import time
import random
from typing import Any, List, Optional, Tuple
import redis
import json

from openpuc_scrapers.models.constants import (
    OPENSCRAPERS_INTERNAL_API_URL,
    OPENSCRAPERS_REDIS_DOMAIN,
)
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase


from openpuc_scrapers.models.jurisdictions import CaseWithJurisdiction, JurisdictionInfo
from openpuc_scrapers.models.timestamp import (
    RFC3339Time,
    is_after,
    rfc_time_now,
    rfctime_serializer,
    time_is_in_yearlist,
)
import requests


from openpuc_scrapers.pipelines.helper_utils import save_json_sync
from openpuc_scrapers.scrapers.base import (
    GenericScraper,
    StateCaseData,
    StateFilingData,
)
import asyncio

default_logger = logging.getLogger(__name__)


def generate_intermediate_object_save_path(
    scraper: GenericScraper[StateCaseData, StateFilingData],
) -> str:
    time_now = rfc_time_now()
    base_path = f"intermediates/{scraper.state}/{scraper.jurisdiction_name}/{rfctime_serializer(time_now)}"

    return base_path


def shuffle_split_string_list(biglist: List[str], split_number: int) -> List[List[str]]:
    """Splits list into N chunks with shuffled order"""
    assert isinstance(biglist, list), "Input must be a list"

    # Create copy to avoid modifying original list
    shuffled = biglist.copy()
    random.shuffle(shuffled)

    # Calculate dynamic chunk size based on desired split count
    chunk_size = max(1, (len(shuffled) + split_number - 1) // split_number)

    list_list = [
        shuffled[i : i + chunk_size] for i in range(0, len(shuffled), chunk_size)
    ]

    # Validate output dimensions
    actual_chunks = len(list_list)
    if actual_chunks != split_number:
        default_logger.warning(
            f"Requested {split_number} chunks but created {actual_chunks} "
            f"(original size: {len(shuffled)}, chunk size: {chunk_size})"
        )

    default_logger.debug(
        f"Split {len(shuffled)} items into {actual_chunks} chunks "
        f"(target: {split_number}), sizes: {[len(chunk) for chunk in list_list]}"
    )

    return list_list


def process_case(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: StateCaseData,
    base_path: str,
) -> GenericCase:
    generic_case = scraper.into_generic_case_data(case)
    case_num = generic_case.case_number
    default_logger.info(f"Successfully made generic case object: {case_num} ")

    # Save state-specific case data
    case_path = f"{base_path}/initial_cases/case_{case_num}.json"
    save_json_sync(path=case_path, data=case)

    # Process filings
    filings_intermediate = scraper.filing_data_intermediate(case)
    filings_path = f"{base_path}/intermediate_caseinfo/case_{case_num}.json"
    save_json_sync(
        path=filings_path,
        data=filings_intermediate,
    )

    filings = scraper.filing_data_from_intermediate(filings_intermediate)
    filings_json_path = f"{base_path}/filings/case_{case_num}.json"
    save_json_sync(
        path=filings_json_path,
        data=filings,
    )
    default_logger.info(
        f"Finished processing case {generic_case.case_name} and found {len(filings)} filings."
    )

    case_specific_generic_cases = []
    for filing in filings:
        generic_filing = scraper.into_generic_filing_data(filing)
        case_specific_generic_cases.append(generic_filing)
    generic_case.filings = case_specific_generic_cases

    default_logger.info(
        f"Finished processing case {generic_case.case_name} and pushing it over to the api. Generic Case Type: {type(generic_case)}"
    )

    jurisdiction_info = JurisdictionInfo(
        country="usa", state=scraper.state, jurisdiction=scraper.jurisdiction_name
    )
    final_obj = CaseWithJurisdiction(case=generic_case, jurisdiction=jurisdiction_info)
    case_json = final_obj.model_dump_json()
    case_json_pythonable = json.loads(case_json)

    default_logger.info(f"successfully got case json for {generic_case.case_name}")

    # NOW THAT THE CASE IS FULLY GENERIC IT SHOULD PUSH ALL THIS STUFF OVER TO RUST
    url = f"{OPENSCRAPERS_INTERNAL_API_URL}/api/cases/submit"
    response = requests.post(url, json=case_json_pythonable)
    response.raise_for_status()

    # INSTEAD OF RETURNING THE CASE REFACTOR THE CODE TO RETURN A SUCCESSFUL SIGNAL
    return GenericCase(
        case_number="Success",
        case_name="Success",
        filings=[],
        opened_date=rfc_time_now(),
    )


def process_case_jsonified_bulk(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    cases: List[str],
    base_path: str,
) -> List[str]:
    return_strings = []
    for i in range(len(cases)):
        try:
            return_strings.append(
                process_case_jsonified(
                    scraper=scraper, case=cases[i], base_path=base_path
                )
            )
        except Exception as e:
            default_logger.error(f"Encountered error while processing case:{e}")
            default_logger.error(traceback.format_exc())
            seconds_time_wait = 10
            default_logger.error(
                f"Continuing next task after waiting {seconds_time_wait} seconds."
            )
            time.sleep(seconds_time_wait)
    return return_strings


def process_case_jsonified(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: str,
    base_path: str,
) -> str:
    case_type = scraper.state_case_type
    case_data = case_type.model_validate_json(case)
    default_logger.info("Successfully deserialized case from json.")

    processed_case = process_case(scraper=scraper, case=case_data, base_path=base_path)
    return processed_case.model_dump_json()


def filter_off_filings_after_date(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    caselist: List[StateCaseData],
    after_date: RFC3339Time,
) -> List[StateCaseData]:
    """Filter cases to only those opened after specified date with validation"""
    filtered_cases = []

    for case in caselist:
        generic_case = scraper.into_generic_case_data(case)
        opened_date = generic_case.opened_date

        if not opened_date:
            default_logger.warning(
                f"Case {generic_case.case_number} missing opened_date, excluding from results"
            )
            continue

        if is_after(rfctime=opened_date, compare_to=after_date):
            filtered_cases.append(case)
        else:
            pass

    default_logger.info(
        f"Date filtering complete - {len(filtered_cases)}/{len(caselist)} "
        f"cases remain after {after_date}"
    )
    return filtered_cases


def filter_off_filings_in_yearlist(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    caselist: List[StateCaseData],
    yearlist: List[int],
) -> List[StateCaseData]:
    """Filter cases to only those opened after specified date with validation"""
    filtered_cases = []

    for case in caselist:
        generic_case = scraper.into_generic_case_data(case)
        opened_date = generic_case.opened_date

        if not opened_date:
            default_logger.warning(
                f"Case {generic_case.case_number} missing opened_date, excluding from results"
            )
            continue
        if len(filtered_cases) == 0:
            filtered_cases.append(case)
        elif time_is_in_yearlist(rfctime=opened_date, years=yearlist):
            filtered_cases.append(case)
        else:
            pass

    default_logger.info(
        f"Date filtering complete - {len(filtered_cases)}/{len(caselist)} "
        f"cases remain after including cases in {yearlist}"
    )
    random.shuffle(filtered_cases)
    return filtered_cases


def get_all_caselist_raw(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    base_path: str,
    year_list: List[int] = [],
) -> List[StateCaseData]:
    """Get full caselist with 2020+ date filtering"""
    # Validate date input

    # Get and save case list
    caselist_intermediate = scraper.universal_caselist_intermediate()
    caselist_path = f"{base_path}/caselist.json"
    save_json_sync(
        path=caselist_path,
        data=caselist_intermediate,
    )

    # Process cases and apply date filter
    state_cases = scraper.universal_caselist_from_intermediate(caselist_intermediate)
    filtered_cases = filter_off_filings_in_yearlist(
        scraper=scraper, caselist=state_cases, yearlist=year_list
    )

    return filtered_cases


def get_all_caselist_raw_jsonified(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    base_path: str,
    year_list: List[int] = [],
) -> List[str]:
    """JSON-serializable version for Airflow XComs"""
    cases = get_all_caselist_raw(scraper, base_path, year_list=year_list)
    return [case.model_dump_json() for case in cases]


def get_new_caselist_since_date(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    after_date: RFC3339Time,
    base_path: str,
    year_list: List[int] = [],
) -> List[StateCaseData]:
    # Get and save updated cases
    updated_intermediate = scraper.updated_cases_since_date_intermediate(after_date)
    updated_path = f"{base_path}/updated_cases.json"
    save_json_sync(
        path=updated_path,
        data=updated_intermediate,
    )

    # Process updated cases
    state_cases = scraper.updated_cases_since_date_from_intermediate(
        updated_intermediate, after_date
    )
    return state_cases


def get_new_caselist_since_date_jsonified(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    after_date: RFC3339Time,
    base_path: str,
) -> List[str]:
    validated_date = after_date
    cases = get_new_caselist_since_date(scraper, validated_date, base_path)
    return [case.model_dump_json() for case in cases]
