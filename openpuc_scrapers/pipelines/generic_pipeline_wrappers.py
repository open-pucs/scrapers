import logging
from typing import Any, List, Optional
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.db.s3_utils import push_case_to_s3_and_db
from openpuc_scrapers.models.constants import (
    OPENSCRAPERS_S3_OBJECT_BUCKET,
)
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase


from openpuc_scrapers.models.timestamp import (
    RFC3339Time,
    rfc_time_from_string,
    rfc_time_now,
    rfctime_serializer,
)
from openpuc_scrapers.pipelines.helper_utils import save_json
from openpuc_scrapers.pipelines.raw_attachment_handling import process_generic_filing
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


def process_case(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: StateCaseData,
    base_path: str,
) -> GenericCase:
    generic_case = scraper.into_generic_case_data(case)
    case_num = generic_case.case_number

    # Save state-specific case data
    case_path = f"{base_path}/initial_cases/case_{case_num}.json"
    save_json(path=case_path, bucket=OPENSCRAPERS_S3_OBJECT_BUCKET, data=case)

    # Process filings
    filings_intermediate = scraper.filing_data_intermediate(case)
    filings_path = f"{base_path}/intermediate_caseinfo/case_{case_num}.json"
    save_json(
        path=filings_path,
        bucket=OPENSCRAPERS_S3_OBJECT_BUCKET,
        data=filings_intermediate,
    )

    filings = scraper.filing_data_from_intermediate(filings_intermediate)
    filings_json_path = f"{base_path}/filings/case_{case_num}.json"
    save_json(
        path=filings_json_path,
        bucket=OPENSCRAPERS_S3_OBJECT_BUCKET,
        data=filings,
    )
    default_logger.info(
        f"Finished processing case {generic_case.case_name} and found {len(filings)} filings."
    )

    case_specific_generic_cases = []
    for filing in filings:
        generic_filing = scraper.into_generic_filing_data(filing)
        case_specific_generic_cases.append(generic_filing)

    default_logger.info("Starting Async Case Processing")

    async def async_shit(case: GenericCase) -> GenericCase:
        tasks = []
        for generic_filing in case_specific_generic_cases:
            # FIXME : What do I do about async with flyte????
            default_logger.info("Adding Generic Filing Task")
            tasks.append(process_generic_filing(generic_filing))
        default_logger.info("Begin Processing Filings")
        result_generic_filings = await asyncio.gather(*tasks)
        default_logger.info("Finish Processing Filings")
        case.filings = result_generic_filings
        await push_case_to_s3_and_db(
            case=case,
            jurisdiction_name=scraper.jurisdiction_name,
            state=scraper.state,
        )
        return case

    return_generic_case = asyncio.run(async_shit(generic_case))
    return return_generic_case


def process_case_jsonified(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: str,
    base_path: str,
) -> str:
    case_type = scraper.state_case_type
    case_data = case_type.model_validate_json(case)

    processed_case = process_case(scraper=scraper, case=case_data, base_path=base_path)
    return processed_case.model_dump_json()


def filter_off_filings_before_date(
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

        if opened_date > after_date:
            filtered_cases.append(case)
            # default_logger.debug(
            #     f"Including case {generic_case.case_number} "
            #     f"(opened: {opened_date}, cutoff: {after_date})"
            # )
        else:
            # default_logger.info(
            #     f"Excluding case {generic_case.case_number} "
            #     f"(opened: {opened_date} <= cutoff: {after_date})"
            # )
            pass

    default_logger.info(
        f"Date filtering complete - {len(filtered_cases)}/{len(caselist)} "
        f"cases remain after {after_date}"
    )
    return filtered_cases


def get_all_caselist_raw(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    base_path: str,
    cutoff_date: Optional[RFC3339Time] = None,
) -> List[StateCaseData]:
    """Get full caselist with 2020+ date filtering"""
    # Validate date input
    if cutoff_date is None:
        cutoff_date = rfc_time_from_string("2020-01-01T00:00:00Z")

    # Get and save case list
    caselist_intermediate = scraper.universal_caselist_intermediate()
    caselist_path = f"{base_path}/caselist.json"
    save_json(
        path=caselist_path,
        bucket=OPENSCRAPERS_S3_OBJECT_BUCKET,
        data=caselist_intermediate,
    )

    # Process cases and apply date filter
    state_cases = scraper.universal_caselist_from_intermediate(caselist_intermediate)
    filtered_cases = filter_off_filings_before_date(
        scraper=scraper, caselist=state_cases, after_date=cutoff_date
    )

    default_logger.info(
        f"Initial caselist filtered from {len(state_cases)} to {len(filtered_cases)} "
        f"cases after {cutoff_date}"
    )
    return filtered_cases


def get_all_caselist_raw_jsonified(
    scraper: GenericScraper[StateCaseData, StateFilingData], base_path: str
) -> List[str]:
    """JSON-serializable version for Airflow XComs"""
    cases = get_all_caselist_raw(scraper, base_path)
    return [case.model_dump_json() for case in cases]


def get_new_caselist_since_date(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    after_date: RFC3339Time,
    base_path: str,
) -> List[StateCaseData]:
    # Get and save updated cases
    updated_intermediate = scraper.updated_cases_since_date_intermediate(after_date)
    updated_path = f"{base_path}/updated_cases.json"
    save_json(
        path=updated_path,
        bucket=OPENSCRAPERS_S3_OBJECT_BUCKET,
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
