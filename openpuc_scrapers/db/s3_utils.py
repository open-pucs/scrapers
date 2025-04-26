from pathlib import Path
from openpuc_scrapers.db.s3_wrapper import S3FileManager
from openpuc_scrapers.db.sql_utilities import set_case_as_updated
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import (
    OPENSCRAPERS_S3_OBJECT_BUCKET,
)
from openpuc_scrapers.models.hashes import Blake2bHash, blake2b_to_str
from openpuc_scrapers.models.raw_attachments import RawAttachment
from openpuc_scrapers.models.timestamp import rfc_time_now


def get_case_s3_key(
    case_name: str, jurisdiction_name: str, state: str, country: str = "usa"
) -> str:
    return f"objects/{country}/{state}/{jurisdiction_name}/{case_name}.json"


def get_raw_attach_obj_key(hash: Blake2bHash) -> str:
    return f"raw/metadata/{blake2b_to_str(hash)}.json"


def get_raw_attach_file_key(hash: Blake2bHash) -> str:
    return f"raw/file/{blake2b_to_str(hash)}"


async def fetch_case_filing_from_s3(
    case_name: str, jurisdiction_name: str, state: str
) -> GenericCase:
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    key = get_case_s3_key(case_name, jurisdiction_name, state)
    raw_case = s3.download_s3_file_to_string(key)
    return GenericCase.model_validate_json(raw_case)


async def fetch_attachment_data_from_s3(hash: Blake2bHash) -> RawAttachment:
    obj_key = get_raw_attach_obj_key(hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    result_str = s3.download_s3_file_to_string(obj_key)
    raw_attach = RawAttachment.model_validate_json(result_str)
    return raw_attach


async def fetch_attachment_file_from_s3(hash: Blake2bHash) -> Path:
    obj_key = get_raw_attach_file_key(hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    result_path = s3.download_s3_file_to_path(obj_key, serve_cache=True)
    if result_path is None:
        raise Exception("Failed to get file from s3")
    return result_path


async def push_raw_attach_to_s3_and_db(raw_att: RawAttachment, file_path: Path) -> None:
    dumped_data = raw_att.model_dump_json()
    obj_key = get_raw_attach_obj_key(raw_att.hash)
    file_key = get_raw_attach_file_key(raw_att.hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    s3.save_string_to_remote_file(key=obj_key, content=dumped_data)
    s3.push_file_to_s3(filepath=file_path, file_upload_key=file_key)
    # TODO: Maybe update db that the file has been updated?


async def push_case_to_s3_and_db(
    case: GenericCase, jurisdiction_name: str, state: str, country: str = "usa"
) -> GenericCase:
    key = get_case_s3_key(
        case_name=case.case_number,
        jurisdiction_name=jurisdiction_name,
        state=state,
        country=country,
    )
    case.indexed_at = rfc_time_now()
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    case_jsonified = case.model_dump_json()
    # Maybe async this in its own thread?
    s3.save_string_to_remote_file(key=key, content=case_jsonified)
    await set_case_as_updated(
        case=case, jurisdiction=jurisdiction_name, state=state, country=country
    )
    return case
