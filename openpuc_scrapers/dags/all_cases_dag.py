from datetime import datetime
from typing import Any
from airflow.decorators import dag, task
from helpers.scraper_utils import (
    generate_intermediate_object_save_path,
    get_scraper,
    process_generic_filing_wrapper,
    S3_SCRAPER_INTERMEDIATE_BUCKET,
)
from openpuc_scrapers.db.s3_utils import push_case_to_s3_and_db
from openpuc_scrapers.pipelines.helper_utils import save_json

default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


@dag(
    default_args=default_args,
    schedule_interval=None,
    params={"state": "default_state", "jurisdiction_name": "default_jurisdiction"},
    tags=["scrapers"],
)
def all_cases_dag():
    @task
    def generate_base_path(state: str, jurisdiction_name: str) -> str:
        return generate_intermediate_object_save_path(state, jurisdiction_name)

    @task
    def get_all_caselist_raw(
        state: str, jurisdiction_name: str, base_path: str
    ) -> list:
        scraper = get_scraper(state, jurisdiction_name)
        caselist_intermediate = scraper.universal_caselist_intermediate()
        save_json(
            path=f"{base_path}/caselist.json",
            bucket=S3_SCRAPER_INTERMEDIATE_BUCKET,
            data=caselist_intermediate,
        )
        return scraper.universal_caselist_from_intermediate(caselist_intermediate)

    @task
    def process_case(
        case: Any, state: str, jurisdiction_name: str, base_path: str
    ) -> Any:

    # DAG structure
    state = "{{ params.state }}"
    jurisdiction = "{{ params.jurisdiction_name }}"
    base_path = generate_base_path(state, jurisdiction)
    cases = get_all_caselist_raw(state, jurisdiction, base_path)
    process_case.partial(
        state=state, jurisdiction_name=jurisdiction, base_path=base_path
    ).expand(case=cases)


all_cases_workflow = all_cases_dag()
