from pydantic import HttpUrl
from openpuc_scrapers.db.airflow_basemodel import AirflowBaseModel
from typing import Any, Dict, Optional

from openpuc_scrapers.models.hashes import Blake2bHash


class GenericAttachment(AirflowBaseModel):
    name: str
    url: HttpUrl
    document_type: Optional[str] = None
    extra_metadata: Dict[str, Any] = {}
    hash: Optional[Blake2bHash] = None
