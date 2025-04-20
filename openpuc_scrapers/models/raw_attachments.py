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
