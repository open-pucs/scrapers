from pydantic import BaseModel
from typing import Any, Dict, Optional

from openpuc_scrapers.models.hashes import Blake2bHash


class GenericAttachment(BaseModel):
    name: str
    url: str
    document_type: Optional[str] = None
    extra_metadata: Dict[str, Any] = {}
    hash: Optional[Blake2bHash] = None
