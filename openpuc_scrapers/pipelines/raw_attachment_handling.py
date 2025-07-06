import logging
from pathlib import Path
from typing import Optional, Tuple, Union
from pydantic import BaseModel, HttpUrl

from openpuc_scrapers.db.s3_utils import (
    does_openscrapers_attachment_exist,
    generate_s3_object_uri_from_key,
    get_raw_attach_file_key,
    get_raw_attach_obj_key,
)
from openpuc_scrapers.db.s3_wrapper import S3FileManager, rand_filepath
from openpuc_scrapers.models.attachment import GenericAttachment
from openpuc_scrapers.models.constants import (
    CRIMSON_URL,
    OPENSCRAPERS_S3_OBJECT_BUCKET,
    TMP_DIR,
)
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.hashes import Blake2bHash, blake2b_hash_from_file
from openpuc_scrapers.models.raw_attachments import (
    AttachmentTextQuality,
    RawAttachment,
    RawAttachmentText,
)
from openpuc_scrapers.models.timestamp import RFC3339Time, rfc_time_now

import aiohttp
import aiofiles
import asyncio

from openpuc_scrapers.scrapers.base import ValidExtension, validate_document_extension

default_logger = logging.getLogger(__name__)


async def process_generic_filing(
    filing: GenericFiling,
) -> Tuple[GenericFiling, int, int]:
    """
    Processes all attachments for a given filing, returning the updated filing
    along with counts of successful and errored attachments.
    """
    attachments = filing.attachments
    tasks = [process_and_shipout_attachment_errorfree(att) for att in attachments]
    new_attachments = await asyncio.gather(*tasks)

    errorfree_attachments = []
    success_count = 0
    error_count = 0
    for att in new_attachments:
        if isinstance(att, GenericAttachment):
            errorfree_attachments.append(att)
            success_count += 1
        else:
            error_count += 1

    filing.attachments = errorfree_attachments
    return filing, success_count, error_count


async def process_and_shipout_attachment_errorfree(
    att: GenericAttachment,
) -> Union[GenericAttachment, str]:
    try:
        return await process_and_shipout_attachment(att=att)
    except Exception as e:
        default_logger.error(f"Encountered exception while processing attachment: {e}")
        error_str = str(e)
        return error_str


async def generate_initial_attachment_text(
    raw_attach: RawAttachment,
) -> Optional[RawAttachmentText]:
    match raw_attach.extension:
        # TODO: Implement processing using pandoc for docx and doc text extraction.
        case "pdf":
            text = await process_pdf_text_using_crimson(raw_attach.hash)

            text_obj = RawAttachmentText(
                quality=AttachmentTextQuality.low,
                text=text,
                language="en",
                timestamp=rfc_time_now(),
            )
            return text_obj

    return None


def validate_file_against_extension(
    extension: ValidExtension, filepath: Path
) -> Optional[Exception]:
    if extension == ValidExtension.PDF:
        # Basic file existence check
        if not filepath.is_file():
            return FileNotFoundError(f"File {filepath} does not exist or is not a file")

        try:
            # Check PDF magic bytes (first 5 characters should be "%PDF-")
            with filepath.open("rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF-"):
                    return ValueError(
                        f"Invalid PDF header: {header[:5].decode('ascii', errors='replace')}"
                    )

        except Exception as e:
            return e

        return None
    return None


async def process_and_shipout_attachment(
    att: GenericAttachment,
) -> GenericAttachment:

    valid_extension = validate_document_extension(att.document_extension or "")
    str_url = str(att.url)
    tmp_filepath = await download_file_from_url_to_path(str_url)
    if isinstance(valid_extension, Exception):
        # raise valid_extension
        # Assume extension is a pdf without any extra info.
        valid_default_extension = ValidExtension.PDF
        # TODO: Upgrade this function so that instead of assuming a pdf and validating against that
        # it can infer the filetype from file metadata.
        match_type_err = validate_file_against_extension(
            valid_default_extension, tmp_filepath
        )
        if match_type_err is not None:
            default_logger.error(
                f"Encountered error processing extension, assumed it was a pdf and failed to validate:  {valid_extension}"
            )
            raise valid_extension
        else:
            att.document_extension = valid_default_extension.value

    else:
        retries = 2
        for attempt in range(retries + 1):
            match_type_err = validate_file_against_extension(
                extension=ValidExtension(valid_extension), filepath=tmp_filepath
            )
            if match_type_err is None:
                att.document_extension = valid_extension
                break
            else:
                if attempt < retries - 1:
                    default_logger.warning(
                        f"Download attempt {attempt + 1} failed: {match_type_err}"
                    )
                    await asyncio.sleep(20)
                    tmp_filepath = await download_file_from_url_to_path(str_url)
                else:
                    raise match_type_err
    hash = blake2b_hash_from_file(tmp_filepath)

    att.hash = hash
    raw_attach = RawAttachment(
        hash=hash, name=att.name, extension=valid_extension, text_objects=[]
    )

    # TODO: Write an algortithm for processing pdf texts on the backend and remove that from the initial scraping operations.
    await push_raw_attach_and_process_text(raw_att=raw_attach, file_path=tmp_filepath)

    return att


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
        await s3.push_file_to_s3_async(
            filepath=file_path, file_upload_key=file_key, immutable=True
        )
        if len(raw_att.text_objects) == 0:
            try:
                new_text = await generate_initial_attachment_text(raw_att)
                if new_text is not None:
                    raw_att.text_objects.append(new_text)
            except Exception as e:
                default_logger.error(e)
    obj_key = get_raw_attach_obj_key(raw_att.hash)
    dumped_data = raw_att.model_dump_json()
    await s3.save_string_to_remote_file_async(key=obj_key, content=dumped_data)
    # Immutable is true for this line since any file will always get saved with the same hash.
    file_exists = await does_openscrapers_attachment_exist(raw_att.hash)
    if not file_exists:
        raise Exception(
            "File failed to upload to s3, and doesnt exist when s3 is polled"
        )


async def download_file_from_url_to_path(url: str) -> Path:
    valid_url = HttpUrl(url=url)
    assert (
        valid_url is not None
    ), "Failed URL Validation"  # Shouldnt be needed since the last line ?should? just throw an exception
    rand_path = TMP_DIR / rand_filepath()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download file from URL: {url}")
            content = await response.read()
            async with aiofiles.open(rand_path, "wb") as f:
                await f.write(content)
    return rand_path


class CrimsonPDFIngestParamsS3(BaseModel):
    s3_uri: str
    langs: Optional[str] = None
    force_ocr: Optional[bool] = None
    paginate: Optional[bool] = None
    disable_image_extraction: Optional[bool] = None
    max_pages: Optional[int] = None


class DocStatusResponse(BaseModel):
    request_id: str
    request_check_url: str
    markdown: Optional[str] = None
    status: str
    success: bool
    completed: bool
    images: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, str]] = None
    error: Optional[str] = None


async def process_pdf_text_using_crimson(attachment_hash_from_s3: Blake2bHash) -> str:
    # build S3 URL from your attachment
    hash_ = attachment_hash_from_s3
    assert hash_ is not None, "Attachment hash cannot be None"
    file_key = get_raw_attach_file_key(hash_)
    s3_url = generate_s3_object_uri_from_key(file_key)

    # create your params
    crimson_params = CrimsonPDFIngestParamsS3(s3_uri=s3_url)
    base_url = CRIMSON_URL.rstrip("/")

    # 1) POST to /v1/ingest/s3
    post_url = f"{base_url}/v1/ingest/s3"
    async with aiohttp.ClientSession() as session:
        async with session.post(post_url, json=crimson_params.dict()) as resp:
            resp.raise_for_status()
            init_data = await resp.json()

        # extract the leaf and build full check URL
        leaf = init_data["request_check_leaf"]
        check_url = f"{base_url}/{leaf.lstrip('/')}"

        # 2) poll every 3 seconds
        while True:
            await asyncio.sleep(3)
            async with session.get(check_url) as status_resp:
                status_resp.raise_for_status()
                status_data = await status_resp.json()

            if status_data.get("completed"):
                if status_data.get("success"):
                    # 3) return the markdown when done
                    markdown = status_data.get("markdown", "")
                    return markdown
                else:
                    error = status_data.get("error")
                    raise Exception(f"Encountered error processing pdf: {error}")

            # else loop again until success


# Example usage:
# result_md = await process_pdf_text_using_crimson(my_attachment, "some/s3/key.pdf")
