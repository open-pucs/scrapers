from openpuc_scrapers.db.s3_wrapper import S3FileManager
from openpuc_scrapers.db.sql_utilities import set_case_as_updated, set_filing_as_updated
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import S3_OBJECT_BUCKET
from openpuc_scrapers.models.timestamp import rfc_time_now


def get_case_s3_key(
    case_name: str, juristiction_name: str, state: str, country: str = "usa"
) -> str:
    return f"{country}/{state}/{juristiction_name}/{case_name}.json"


async def fetch_case_filing_from_s3(
    case_name: str, juristiction_name: str, state: str
) -> GenericCase:
    s3 = S3FileManager(bucket=S3_OBJECT_BUCKET)
    key = get_case_s3_key(case_name, juristiction_name, state)
    raw_case = s3.download_s3_file_to_string(key)
    return GenericCase.model_validate_json(raw_case)


async def push_case_to_s3_and_db(
    case: GenericCase, juristiction_name: str, state: str, country: str = "usa"
) -> GenericCase:
    key = get_case_s3_key(
        case_name=case.case_number,
        juristiction_name=juristiction_name,
        state=state,
        country=country,
    )
    case.indexed_at = rfc_time_now()
    s3 = S3FileManager(bucket=S3_OBJECT_BUCKET)
    case_jsonified = case.model_dump_json()
    s3.save_string_to_remote_file(key=key, content=case_jsonified)
    await set_case_as_updated(
        case=case, juristiction=juristiction_name, state=state, country=country
    )
    return case
