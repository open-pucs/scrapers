from enum import Enum
from typing import List
from pydantic import BaseModel

from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.timestamp import RFC3339Time


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
