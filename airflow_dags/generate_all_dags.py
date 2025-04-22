from datetime import datetime
from typing import Any, List
from airflow.decorators import dag, task
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw_jsonified,
    get_new_caselist_since_date_jsonified,
    process_case_jsonified,
)
from openpuc_scrapers.scrapers.scraper_lookup import SCRAPER_REGISTRY, ScraperInfoObject


default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


def create_scraper_allcases_dag(scraper_info: ScraperInfoObject):
    """Factory function to create DAG for a specific scraper"""

    @dag(
        default_args=default_args,
        schedule_interval=None,
        dag_id=f"{scraper_info.id}_all_cases",
        tags=["scrapers", scraper_info.id],
    )
    def scraper_dag():
        @task
        def get_all_caselist_raw_airflow(scraper: Any, base_path: str) -> List[str]:
            return get_all_caselist_raw_jsonified(scraper=scraper, base_path=base_path)

        @task
        def process_case_airflow(scraper: Any, case: str, base_path: str) -> str:
            return process_case_jsonified(
                scraper=scraper, case=case, base_path=base_path
            )

        # DAG structure - now uses fixed scraper name
        scraper = (scraper_info.object_type)()
        base_path = generate_intermediate_object_save_path(scraper)
        cases = get_all_caselist_raw_airflow(scraper=scraper, base_path=base_path)

        return process_case_airflow.expand(
            scraper=[scraper], case=cases, base_path=[base_path]
        )

    return scraper_dag()


def create_scraper_newcases_dag(scraper_info: ScraperInfoObject):
    @dag(
        default_args=default_args,
        schedule_interval="@daily",  # Can be adjusted based on needs
        dag_id=f"{scraper_info.id}_new_cases",
        params={
            "after_date": "2023-01-01",  # Default date, will be overridden at runtime
        },
        tags=["scrapers", "incremental", scraper_info.id],
    )
    def new_cases_since_date_dag():
        @task
        def get_caselist_since_date_task(scraper: Any, base_path: str) -> List[str]:
            after_date = datetime.fromisoformat("{{ params.after_date }}")
            return get_new_caselist_since_date_jsonified(
                scraper=scraper, after_date=after_date, base_path=base_path
            )

        @task
        def process_case_airflow(scraper: Any, case: str, base_path: str) -> str:
            return process_case_jsonified(
                scraper=scraper, case=case, base_path=base_path
            )

        # DAG structure
        scraper = (scraper_info.object_type)()
        base_path = generate_intermediate_object_save_path(scraper)

        new_cases = get_caselist_since_date_task(scraper=scraper, base_path=base_path)

        return process_case_airflow.expand(
            scraper=[scraper], case=new_cases, base_path=[base_path]
        )

    return new_cases_since_date_dag()


# Generate DAGs for all scrapers
for scraper_info in SCRAPER_REGISTRY:
    allcases_dag_id = f"{scraper_info.id}_allcases_dag"
    globals()[allcases_dag_id] = create_scraper_allcases_dag(scraper_info=scraper_info)
    newcases_dag_id = f"{scraper_info.id}_newcases_dag"
    globals()[newcases_dag_id] = create_scraper_newcases_dag(scraper_info=scraper_info)
