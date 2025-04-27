from enum import Enum
from hmac import new
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from openpuc_scrapers.db.s3_utils import push_raw_attach_to_s3_and_db
from openpuc_scrapers.db.s3_wrapper import S3FileManager, rand_filepath
from openpuc_scrapers.models.attachment import GenericAttachment
from openpuc_scrapers.models.constants import OPENSCRAPERS_S3_OBJECT_BUCKET, TMP_DIR
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


import pymupdf4llm
import pymupdf

default_logger = logging.getLogger(__name__)


async def process_generic_filing(filing: GenericFiling) -> GenericFiling:
    default_logger.info(f"Starting to process filing{filing.name}")
    attachments = filing.attachments
    tasks = []
    for att in attachments:
        tasks.append(process_and_shipout_initial_attachment(att))
    new_attachments = await asyncio.gather(*tasks)
    default_logger.info(f"Finished processing filing{filing.name}")
    filing.attachments = new_attachments
    return filing


async def process_and_shipout_initial_attachment(
    att: GenericAttachment,
) -> GenericAttachment:
    if att.document_extension is None or att.document_extension == "":
        raise ValueError(
            "Cannot Process Attachment if document_extension is None or empty"
        )
    str_url = str(att.url)
    tmp_filepath = await download_file_from_url_to_path(str_url)
    hash = blake2b_hash_from_file(tmp_filepath)
    att.hash = hash
    raw_attach = RawAttachment(
        hash=hash, name=att.name, extension=att.document_extension, text_objects=[]
    )

    async def generate_initial_attachment_text(
        raw_attach: RawAttachment, file_path: Path
    ) -> Optional[RawAttachmentText]:
        match raw_attach.extension:
            # TODO: Implement processing using pandoc for docx and doc text extraction.
            case "pdf":
                text = parse_raw_pdf_text(file_path)
                text_obj = RawAttachmentText(
                    quality=AttachmentTextQuality.low,
                    text=text,
                    language="en",
                    timestamp=rfc_time_now(),
                )
                return text_obj

        return None

    result_text = await generate_initial_attachment_text(raw_attach, tmp_filepath)
    if result_text is not None:
        raw_attach.text_objects = [result_text]

    await push_raw_attach_to_s3_and_db(raw_attach, tmp_filepath)
    return att


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


def parse_raw_pdf_text(pdf_file_path: Path) -> str:
    full_text = []

    def combine_pdf_text_pages(page_texts: List[str]) -> str:
        def page_seperator(page_num: int) -> str:
            return f"<!-- Page {page_num} -->"

        complete_text = ""
        for index in range(len(page_texts)):
            complete_text += page_texts[index] + page_seperator(index + 1)
        return complete_text

    with pymupdf.open(pdf_file_path) as doc:
        markdown_chunked_objects: List[dict] = pymupdf4llm.to_markdown(
            doc, page_chunks=True
        )  # This seems to run contrary to their own documentation
        for chunked_page in markdown_chunked_objects:
            full_text.append(chunked_page.get("text"))

    return combine_pdf_text_pages(page_texts=full_text)
