from datetime import datetime
from typing import Any, List
from airflow.decorators import dag, task
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw_jsonified,
    process_case_jsonified,
)
from openpuc_scrapers.scrapers.scraper_lookup import (
    get_scraper_type_from_name_default_dummy,
)


default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


@dag(
    default_args=default_args,
    schedule_interval=None,
    params={"scraper_name": "unknown"},
    tags=["scrapers"],
)
def all_cases_dag():
    # TODO: Add the types for this later, rn I am wanting to do things as simply as possible to avoid weird shit

    @task
    def get_all_caselist_raw_airflow(scraper: Any, base_path: str) -> List[str]:
        return get_all_caselist_raw_jsonified(scraper=scraper, base_path=base_path)

    @task
    def process_case_airflow(scraper: Any, case: str, base_path: str) -> str:
        return process_case_jsonified(scraper=scraper, case=case, base_path=base_path)

    # DAG structure
    scraper_name = "{{ params.scraper_name }}"
    scraper_type = get_scraper_type_from_name_default_dummy(scraper_name)
    scraper = scraper_type()
    base_path = generate_intermediate_object_save_path(scraper)
    cases = get_all_caselist_raw_airflow(scraper=scraper, base_path=base_path)

    # Process cases using Airflow's dynamic task mapping
    return process_case_airflow.expand(
        scraper=[scraper], case=cases, base_path=[base_path]
    )


all_cases_workflow = all_cases_dag()
