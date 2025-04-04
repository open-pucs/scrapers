from enum import Enum
from pathlib import Path
from typing import List
from pydantic import BaseModel

from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.timestamp import RFC3339Time


import fitz  # PyMuPDF


class AttachmentTextQuality(Enum):
    low = 0
    # Leave room for qualities in between low and high for later usage
    high = 100


class RawAttachmentText(BaseModel):
    quality: AttachmentTextQuality
    language: str
    text: str
    timestamp: RFC3339Time


class RawAttachment(BaseModel):
    hash: Blake2bHash
    name: str
    extension: str
    text_objects: List[RawAttachmentText]


def get_highest_quality_text(attach: RawAttachment) -> str:
    def attach_ranker(att: RawAttachmentText):
        # Scale down timestamp to be a small fraction so quality remains primary factor
        # timestamp_value = att.time.timestamp() / (2**32)  # breaks on unix 2038
        # return att.quality.value + timestamp_value
        return att.quality.value

    best_attachment_text = max(attach.text_objects, key=attach_ranker)
    return best_attachment_text.text


def get_raw_attachment_object(hash: Blake2bHash) -> RawAttachment:
    return RawAttachment(hash=hash, name="", extension="", text_objects=[])


def combine_pdf_text_pages(page_texts: List[str]) -> str:
    def page_seperator(page_num: int) -> str:
        return f"<!-- Page {page_num} -->"

    complete_text = ""
    for index in range(len(page_texts)):
        complete_text += page_texts[index] + page_seperator(index + 1)
    return complete_text


def parse_raw_pdf_text(pdf_file_path: Path) -> str:

    full_text = []
    with fitz.open(pdf_file_path) as doc:
        for page in doc:
            text = page.get_text()
            full_text.append(text)

    return combine_pdf_text_pages(page_texts=full_text)
