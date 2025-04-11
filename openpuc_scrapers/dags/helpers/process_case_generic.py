from typing import Any

from openpuc_scrapers.db.s3_utils import push_case_to_s3_and_db
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import S3_SCRAPER_INTERMEDIATE_BUCKET
from openpuc_scrapers.pipelines.helper_utils import save_json
from openpuc_scrapers.scrapers.base import GenericScraper
import asyncio


def process_generic_case_helper(
    case: Any, scraper: GenericScraper, base_path: str
) -> Any:
    state = scraper.state
    jurisdiction_name = scraper.jurisdiction_name

    generic_case = scraper.into_generic_case_data(case)

    # Save case data
    case_path = f"{base_path}/cases/case_{generic_case.case_number}.json"
    save_json(case_path, S3_SCRAPER_INTERMEDIATE_BUCKET, case)

    # Process filings
    filings_intermediate = scraper.filing_data_intermediate(case)
    filings_path = f"{base_path}/filings/case_{generic_case.case_number}.json"
    save_json(filings_path, S3_SCRAPER_INTERMEDIATE_BUCKET, filings_intermediate)

    filings = scraper.filing_data_from_intermediate(filings_intermediate)
    for filing in filings:
        generic_filing = scraper.into_generic_filing_data(filing)
        process_generic_filing_helper(generic_filing, scraper, base_path)

    generic_case.filings = filings
    asyncio.run(
        push_case_to_s3_and_db(
            case=generic_case, jurisdiction_name=jurisdiction_name, state=state
        )
    )
    return generic_case


def process_generic_filing_helper(
    generic_filing: Any, scraper: GenericScraper, base_path: str
):
    state = scraper.state
    jurisdiction_name = scraper.jurisdiction_name
