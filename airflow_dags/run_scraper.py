import argparse
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw_jsonified,
    get_new_caselist_since_date_jsonified,
    process_case_jsonified,
)
from openpuc_scrapers.scrapers.scraper_lookup import SCRAPER_REGISTRY, ScraperInfoObject

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_all_cases(scraper_info: ScraperInfoObject, years: list[int] | None):
    """Run the scraper for all cases."""
    scraper = scraper_info.object_type()
    base_path = generate_intermediate_object_save_path(scraper)
    logging.info(f"Running scraper for all cases for {scraper_info.id}")

    if not years:
        years = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
    logging.info(f"Filtering for years: {years}")

    cases = get_all_caselist_raw_jsonified(
        scraper=scraper, base_path=base_path, year_list=years
    )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_case_jsonified, scraper, case, base_path)
            for case in cases
        ]
        for future in as_completed(futures):
            try:
                result = future.result()
                logging.info(f"Successfully processed case: {result}")
            except Exception as e:
                logging.error(f"Error processing case: {e}")


def run_new_cases(scraper_info: ScraperInfoObject, after_date: str | None):
    """Run the scraper for new cases."""
    scraper = scraper_info.object_type()
    base_path = generate_intermediate_object_save_path(scraper)

    if after_date:
        after_date_dt = datetime.fromisoformat(after_date)
    else:
        after_date_dt = datetime(2023, 1, 1)

    logging.info(
        f"Running scraper for new cases for {scraper_info.id} after {after_date_dt.date()}"
    )

    cases = get_new_caselist_since_date_jsonified(
        scraper=scraper, after_date=after_date_dt, base_path=base_path
    )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(process_case_jsonified, scraper, case, base_path)
            for case in cases
        ]
        for future in as_completed(futures):
            try:
                result = future.result()
                logging.info(f"Successfully processed case: {result}")
            except Exception as e:
                logging.error(f"Error processing case: {e}")


def run_test_single_docket(scraper_info: ScraperInfoObject):
    """Run the scraper for a single test docket."""
    scraper = scraper_info.object_type()
    base_path = generate_intermediate_object_save_path(scraper)
    case = scraper_info.test_singular_docket
    if case is None:
        logging.error(f"No test docket defined for scraper {scraper_info.id}")
        return

    case_json = case.model_dump_json()

    logging.info(f"Running scraper for single test docket for {scraper_info.id}")

    try:
        result = process_case_jsonified(
            scraper=scraper, case=case_json, base_path=base_path
        )
        logging.info(f"Successfully processed case: {result}")
    except Exception as e:
        logging.error(f"Error processing case: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run scrapers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scraper_choices = [scraper.id for scraper in SCRAPER_REGISTRY]

    # Sub-parser for all-cases
    parser_all_cases = subparsers.add_parser(
        "all-cases", help="Run the scraper for all cases."
    )
    parser_all_cases.add_argument(
        "--scraper", required=True, choices=scraper_choices, help="The scraper to run."
    )
    parser_all_cases.add_argument(
        "--years", help="A comma-separated list of years to scrape."
    )

    # Sub-parser for new-cases
    parser_new_cases = subparsers.add_parser(
        "new-cases", help="Run the scraper for new cases."
    )
    parser_new_cases.add_argument(
        "--scraper", required=True, choices=scraper_choices, help="The scraper to run."
    )
    parser_new_cases.add_argument(
        "--after-date", help="The date to scrape new cases after (YYYY-MM-DD)."
    )

    # Sub-parser for test-single-docket
    parser_test_single_docket = subparsers.add_parser(
        "test-single-docket", help="Run the scraper for a single test docket."
    )
    parser_test_single_docket.add_argument(
        "--scraper", required=True, choices=scraper_choices, help="The scraper to run."
    )

    args = parser.parse_args()

    scraper_info = next((s for s in SCRAPER_REGISTRY if s.id == args.scraper), None)
    if not scraper_info:
        logging.error(f"Scraper '{args.scraper}' not found.")
        return

    if args.command == "all-cases":
        years = [int(y) for y in args.years.split(",")] if args.years else None
        run_all_cases(scraper_info, years)
    elif args.command == "new-cases":
        run_new_cases(scraper_info, args.after_date)
    elif args.command == "test-single-docket":
        run_test_single_docket(scraper_info)


if __name__ == "__main__":
    main()
