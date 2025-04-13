from datetime import datetime
from typing import Any, List
from airflow.decorators import dag, task
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw,
    get_new_caselist_since_date,
    process_case,
)
from openpuc_scrapers.scrapers.scraper_lookup import (
    get_scraper_type_from_name_unvalidated,
)

# from openpuc_scrapers.models.case import GenericCase
# from openpuc_scrapers.scrapers.base import StateCaseData, StateFilingData
# from functools import partial

default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


@dag(
    default_args=default_args,
    schedule_interval="@daily",  # Can be adjusted based on needs
    params={
        "scraper_name": "unknown",
        "after_date": "2023-01-01",  # Default date, will be overridden at runtime
    },
    tags=["scrapers", "incremental"],
)
def new_cases_since_date_dag():
    @task
    def get_caselist_since_date_task(scraper: Any, base_path: str) -> List[Any]:
        after_date = datetime.fromisoformat("{{ params.after_date }}")
        return get_new_caselist_since_date(
            scraper=scraper, after_date=after_date, base_path=base_path
        )

    # Reuse existing processing task
    @task
    def process_case_airflow(scraper: Any, case: Any, base_path: str) -> Any:
        return process_case(scraper=scraper, case=case, base_path=base_path)

    # DAG structure
    scraper_name = "{{ params.scraper_name }}"
    scraper_type = get_scraper_type_from_name_unvalidated(scraper_name)
    scraper = scraper_type()
    base_path = generate_intermediate_object_save_path(scraper)

    new_cases = get_caselist_since_date_task(scraper=scraper, base_path=base_path)

    for case in new_cases:
        process_case_airflow(scraper=scraper, case=case, base_path=base_path)


new_cases_workflow = new_cases_since_date_dag()
