import asyncio
import json
from typing import Any, Optional
from pydantic import BaseModel
import requests

from openpuc_scrapers.models.constants import OPENSCRAPERS_INTERNAL_API_URL


def save_json_sync(path: str, data: Any, bucket: Optional[str] = None) -> None:
    if data.isinstance(BaseModel):
        data = data.dict()
    url = f"{OPENSCRAPERS_INTERNAL_API_URL}/admin/write_openscrapers_s3_json"
    payload = {"key": path, "contents": data}
    if bucket is not None:
        payload["bucket"] = bucket
    response = requests.post(url, json=payload)
    response.raise_for_status()
