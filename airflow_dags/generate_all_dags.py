from datetime import datetime, timedelta
import os
from typing import Any, List, Tuple
from airflow.decorators import dag, task
from openpuc_scrapers.db.s3_wrapper import rand_string
from openpuc_scrapers.models.timestamp import rfc_time_now, rfctime_serializer
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw_jsonified,
    get_new_caselist_since_date_jsonified,
    process_case_jsonified,
    process_case_jsonified_bulk,
    shuffle_split_string_list,
)
from openpuc_scrapers.pipelines.misc_testing import test_selenium_connection
from openpuc_scrapers.scrapers.scraper_lookup import SCRAPER_REGISTRY, ScraperInfoObject


# test_selenium_connection()
default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


def create_scraper_allcases_dag(scraper_info: ScraperInfoObject) -> Any:
    """Factory function to create DAG for a specific scraper with queue-based processing"""

    @dag(
        default_args=default_args,
        schedule_interval=None,
        dag_id=f"{scraper_info.id}_all_cases",
        tags=["scrapers", "all_cases", scraper_info.id],
        max_active_tasks=20,
        concurrency=10,
    )
    def scraper_dag():
        @task
        def get_all_caselist_raw_airflow(scraper: Any, base_path: str) -> List[str]:
            json_list = get_all_caselist_raw_jsonified(
                scraper=scraper, base_path=base_path
            )
            return json_list

        @task
        def initialize_processing_queue(cases: List[str]) -> str:
            """Initialize Redis queue with all case IDs"""
            from redis import Redis
            from json import dumps
            from openpuc_scrapers.models.constants import OPENSCRAPERS_REDIS_DOMAIN
            import random

            r = Redis(host=OPENSCRAPERS_REDIS_DOMAIN, port=6379, db=0)
            queue_key = f"{scraper_info.id}_case_queue_{rand_string()}"

            random.shuffle(cases)

            # Clear previous queue contents
            r.delete(queue_key)

            # Add all cases as JSON objects
            pipeline = r.pipeline()
            for case in cases:
                pipeline.rpush(
                    queue_key,
                    dumps(
                        {
                            "scraper_id": scraper_info.id,
                            "case_json": case,
                            "base_path": base_path,
                        }
                    ),
                )
            pipeline.execute()

            return queue_key

        @task(
            # execution_timeout=timedelta(minutes=15),
        )
        def process_concurrent_cases_airflow(queue_key: str) -> dict:
            """Process next case from queue with atomic pop operation"""
            from redis import Redis
            from json import loads, dumps

            from openpuc_scrapers.models.constants import OPENSCRAPERS_REDIS_DOMAIN
            import logging

            default_logger = logging.getLogger(__name__)

            r = Redis(host=OPENSCRAPERS_REDIS_DOMAIN, port=6379, db=0)
            errored_json_redis_key = f"{queue_key}-errored"
            scraper = (scraper_info.object_type)()
            max_iter_per_concurrent_node = 100_000
            completed_json = []
            errored_json = []
            for _ in range(max_iter_per_concurrent_node):
                case_data = r.lpop(queue_key)

                if not case_data:
                    return {
                        "status": "COMPLETED",
                        "results": completed_json,
                        "errored": errored_json,
                    }

                case_obj = loads(case_data)
                try:
                    result = process_case_jsonified(
                        scraper=scraper,
                        case=case_obj["case_json"],
                        base_path=case_obj["base_path"],
                    )
                    completed_json.append(result)
                except Exception as e:
                    default_logger.error(
                        f"Encountered exception while processing doc: {e}"
                    )
                    error_dict = {
                        "case_json": case_data,
                        "timestamp": rfctime_serializer(rfc_time_now()),
                        "error": str(e),
                    }
                    default_logger.error(
                        f"Pushing error data to redis queue: {errored_json_redis_key}"
                    )
                    r.rpush(errored_json_redis_key, dumps(error_dict))

                    default_logger.error(
                        f"So far {len(errored_json)} have failed, compared to {len(completed_json)} successes."
                    )

            return {
                "status": "ERROR",
                "error": f"Individual node tried to do more then {max_iter_per_concurrent_node} tasks",
                "results": completed_json,
                "errored": errored_json,
            }

        # DAG structure
        scraper = (scraper_info.object_type)()
        base_path = generate_intermediate_object_save_path(scraper)
        cases = get_all_caselist_raw_airflow(scraper=scraper, base_path=base_path)
        queue_key = initialize_processing_queue(cases=cases)

        # Dynamic parallel processing with queue size awareness
        concurrency_limit = 1

        # Create independent parallel tasks that will each process until queue is empty
        for _ in range(concurrency_limit):
            process_concurrent_cases_airflow(queue_key)

    return scraper_dag()


def create_scraper_allcases_dag_simple(scraper_info: ScraperInfoObject) -> Any:
    """Factory function to create DAG for a specific scraper"""

    @dag(
        default_args=default_args,
        schedule_interval=None,
        dag_id=f"{scraper_info.id}_all_cases",
        tags=["scrapers", "all_cases", scraper_info.id],
        max_active_tasks=20,  # Overall DAG concurrency
        concurrency=10,  # Match task concurrency
    )
    def scraper_dag():
        @task
        def get_all_caselist_raw_airflow(scraper: Any, base_path: str) -> List[str]:
            return get_all_caselist_raw_jsonified(scraper=scraper, base_path=base_path)

        @task
        def shuffle_split_string_list_airflow(
            biglist: List[str], split_number: int
        ) -> List[List[str]]:
            return shuffle_split_string_list(biglist=biglist, split_number=split_number)

        @task(
            execution_timeout=timedelta(minutes=15),  # Add safety timeout
        )
        def process_case_airflow_bulk(
            scraper: Any, cases: List[str], base_path: str
        ) -> List[str]:
            """Process individual case with concurrency limits and retries"""

            return process_case_jsonified_bulk(
                scraper=scraper, cases=cases, base_path=base_path
            )

        @task(
            execution_timeout=timedelta(minutes=15),  # Add safety timeout
        )
        def process_case_airflow(scraper: Any, case: str, base_path: str) -> str:
            """Process individual case with concurrency limits and retries"""

            return process_case_jsonified(
                scraper=scraper, case=case, base_path=base_path
            )

        # DAG structure - now uses fixed scraper name
        scraper = (scraper_info.object_type)()
        base_path = generate_intermediate_object_save_path(scraper)
        cases = get_all_caselist_raw_airflow(scraper=scraper, base_path=base_path)
        concurrency_num = 10
        randomized_subcaselist = shuffle_split_string_list_airflow(
            biglist=cases, split_number=concurrency_num
        )
        # break this into

        return process_case_airflow_bulk.expand(
            scraper=[scraper], cases=randomized_subcaselist, base_path=[base_path]
        )

    return scraper_dag()


def create_scraper_newcases_dag(scraper_info: ScraperInfoObject) -> Any:
    @dag(
        default_args=default_args,
        schedule_interval="@daily",  # Can be adjusted based on needs
        dag_id=f"{scraper_info.id}_new_cases",
        params={
            "after_date": "2023-01-01",  # Default date, will be overridden at runtime
        },
        tags=["scrapers", "incremental", scraper_info.id],
        max_active_tasks=20,  # Overall DAG concurrency
    )
    def new_cases_since_date_dag():
        @task
        def get_caselist_since_date_task(scraper: Any, base_path: str) -> List[str]:
            after_date = datetime.fromisoformat("{{ params.after_date }}")
            return get_new_caselist_since_date_jsonified(
                scraper=scraper, after_date=after_date, base_path=base_path
            )

        @task(
            execution_timeout=timedelta(minutes=15),  # Add safety timeout
        )
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


def create_single_docket_test_dag(scraper_info: ScraperInfoObject) -> Any:
    """Factory function to create DAG for a specific scraper"""

    @dag(
        default_args=default_args,
        schedule_interval=None,
        dag_id=f"{scraper_info.id}_test_single_docket",
        tags=["scrapers", "test", scraper_info.id],
    )
    def scraper_dag():

        @task
        def process_case_airflow(scraper: Any, case: str, base_path: str) -> str:
            return process_case_jsonified(
                scraper=scraper, case=case, base_path=base_path
            )

        # DAG structure - now uses fixed scraper name
        scraper = (scraper_info.object_type)()
        base_path = generate_intermediate_object_save_path(scraper)
        case = scraper_info.test_singular_docket
        assert case is not None
        case_json = case.model_dump_json()

        return process_case_airflow(
            scraper=scraper,
            case=case_json,
            base_path=base_path,
        )

    return scraper_dag()


# Generate DAGs for all scrapers
for scraper_info in SCRAPER_REGISTRY:
    allcases_dag_id = f"{scraper_info.id}_allcases_dag"
    globals()[allcases_dag_id] = create_scraper_allcases_dag(scraper_info=scraper_info)
    newcases_dag_id = f"{scraper_info.id}_newcases_dag"
    globals()[newcases_dag_id] = create_scraper_newcases_dag(scraper_info=scraper_info)
    if scraper_info.test_singular_docket is not None:
        testsingulardocket_dag_id = f"{scraper_info.id}_singular_docket_test_dag"
        globals()[testsingulardocket_dag_id] = create_single_docket_test_dag(
            scraper_info=scraper_info
        )
