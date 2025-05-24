import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from openpuc_scrapers.db.s3_wrapper import S3FileManager
from openpuc_scrapers.db.sql_utilities import CaseInfo, set_case_as_updated
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import (
    OPENSCRAPERS_S3_ENDPOINT,
    OPENSCRAPERS_S3_OBJECT_BUCKET,
)
from openpuc_scrapers.models.hashes import Blake2bHash, blake2b_to_str
from openpuc_scrapers.models.raw_attachments import RawAttachment
from openpuc_scrapers.models.timestamp import rfc_time_now
from openpuc_scrapers.pipelines.raw_attachment_handling import (
    generate_initial_attachment_text,
)


default_logger = logging.getLogger(__name__)


def get_case_s3_key(
    case_name: str, jurisdiction_name: str, state: str, country: str = "usa"
) -> str:
    return f"objects/{country}/{state}/{jurisdiction_name}/{case_name}.json"


def get_raw_attach_obj_key(hash: Blake2bHash) -> str:
    return f"raw/metadata/{blake2b_to_str(hash)}.json"


def get_raw_attach_file_key(hash: Blake2bHash) -> str:
    return f"raw/file/{blake2b_to_str(hash)}"


def generate_s3_object_uri_from_key(key: str) -> str:
    stripped_endpoint = OPENSCRAPERS_S3_ENDPOINT.removeprefix("https://")
    return f"https://{OPENSCRAPERS_S3_OBJECT_BUCKET}.{stripped_endpoint}/{key}"


async def fetch_case_filing_from_s3(
    case_name: str, jurisdiction_name: str, state: str, country: str = "usa"
) -> GenericCase:
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    key = get_case_s3_key(
        case_name=case_name,
        jurisdiction_name=jurisdiction_name,
        state=state,
        country=country,
    )
    raw_case = await s3.download_s3_file_to_string_async(file_name=key)
    return GenericCase.model_validate_json(raw_case)


async def fetch_attachment_data_from_s3(hash: Blake2bHash) -> RawAttachment:
    obj_key = get_raw_attach_obj_key(hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    result_str = await s3.download_s3_file_to_string_async(file_name=obj_key)
    raw_attach = RawAttachment.model_validate_json(result_str)
    return raw_attach


async def fetch_attachment_file_from_s3(hash: Blake2bHash) -> Path:
    obj_key = get_raw_attach_file_key(hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    result_path = await s3.download_s3_file_to_path_async(
        file_name=obj_key, serve_cache=True
    )
    if result_path is None:
        raise Exception("Failed to get file from s3")
    return result_path


async def push_raw_attach_to_s3_and_db(
    raw_att: RawAttachment, file_path: Optional[Path], file_only: bool = False
) -> None:

    dumped_data = raw_att.model_dump_json()
    obj_key = get_raw_attach_obj_key(raw_att.hash)
    file_key = get_raw_attach_file_key(raw_att.hash)
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    if not file_only:
        await s3.save_string_to_remote_file_async(key=obj_key, content=dumped_data)
    # Immutable is true for this line since any file will always get saved with the same hash.
    if file_path is None:
        does_exist = await s3.check_if_file_exists(file_upload_key=file_key)
        if does_exist:
            default_logger.info(
                f"File with hash {raw_att.hash} already exists on s3. Skipping upload"
            )
            return None
        else:
            error_string = f"File with hash {raw_att.hash} does not exist on s3 and no uploaded file was provided."
            default_logger.error(error_string)
            raise FileNotFoundError(error_string)
    await s3.push_file_to_s3_async(
        filepath=file_path, file_upload_key=file_key, immutable=True
    )


async def push_raw_attach_and_process_text(
    raw_att: RawAttachment, file_path: Path
) -> None:

    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    file_exists = await does_openscrapers_attachment_exist(raw_att.hash)

    if file_exists:
        s3_metadata_string = await s3.download_s3_file_to_string_async(
            get_raw_attach_obj_key(raw_att.hash)
        )
        s3_metadata = RawAttachment.model_validate_json(s3_metadata_string)
        if len(raw_att.text_objects) == 0:
            if len(s3_metadata.text_objects) == 0:
                new_text = await generate_initial_attachment_text(raw_att)
                if new_text is not None:
                    s3_metadata.text_objects.append(new_text)
            raw_att.text_objects.extend(s3_metadata.text_objects)
    else:
        file_key = get_raw_attach_file_key(raw_att.hash)
        if len(raw_att.text_objects) == 0:
            new_text = await generate_initial_attachment_text(raw_att)
            if new_text is not None:
                raw_att.text_objects.append(new_text)
        await s3.push_file_to_s3_async(
            filepath=file_path, file_upload_key=file_key, immutable=True
        )
    obj_key = get_raw_attach_obj_key(raw_att.hash)
    dumped_data = raw_att.model_dump_json()
    await s3.save_string_to_remote_file_async(key=obj_key, content=dumped_data)
    # Immutable is true for this line since any file will always get saved with the same hash.
    file_exists = await does_openscrapers_attachment_exist(raw_att.hash)
    if not file_exists:
        raise Exception(
            "File failed to upload to s3, and doesnt exist when s3 is polled"
        )


async def does_openscrapers_attachment_exist(hash: Blake2bHash) -> bool:
    bucket = OPENSCRAPERS_S3_OBJECT_BUCKET
    s3 = S3FileManager(bucket=bucket)
    obj_key = get_raw_attach_obj_key(hash)
    file_key = get_raw_attach_file_key(hash)
    try:
        do_files_exist_list = await asyncio.gather(
            s3.check_if_file_exists(file_upload_key=obj_key, bucket=bucket),
            s3.check_if_file_exists(file_upload_key=file_key, bucket=bucket),
        )
        return do_files_exist_list[0] and do_files_exist_list[1]
    except Exception as e:
        return False


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
    await s3.save_string_to_remote_file_async(key=key, content=case_jsonified)
    case_info = CaseInfo(
        case=case, jurisdiction_name=jurisdiction_name, state=state, country=country
    )
    await set_case_as_updated(case_info=case_info)
    return case


async def list_cases_for_jurisdiction(
    jurisdiction_name: str, state: str, country: str = "usa"
) -> List[str]:
    """
    Returns all case names stored in S3 for a given jurisdiction.

    Args:
        jurisdiction_name: Name of the legal jurisdiction
        state: State abbreviation
        country: Country code (default: 'usa')

    Returns:
        List of case numbers/filenames found in the S3 bucket
    """
    s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
    prefix = f"objects/{country}/{state}/{jurisdiction_name}/"

    # Get all keys matching the jurisdiction prefix
    keys = await s3.list_objects_with_prefix_async(prefix)

    # Extract case names from S3 keys
    case_names = []
    for key in keys:
        if key.endswith(".json"):
            # Split key path and remove .json extension
            filename = key.split("/")[-1]
            case_name = filename[:-5]
            case_names.append(case_name)

    return case_names
