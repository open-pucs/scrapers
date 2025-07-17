import asyncio
import json
import logging
from typing import Any, Optional
from pydantic import BaseModel
import requests

from openpuc_scrapers.models.constants import OPENSCRAPERS_INTERNAL_API_URL


default_logger = logging.getLogger(__name__)


def save_json_sync(path: str, data: Any, bucket: Optional[str] = None) -> None:
    try:
        url = f"{OPENSCRAPERS_INTERNAL_API_URL}/admin/write_openscrapers_s3_json"
        payload = {"key": path, "contents": data}
        if isinstance(data, BaseModel):
            payload["data"] = data.model_dump()
        if bucket is not None:
            payload["bucket"] = bucket
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        default_logger.error(
            f"Could not convert data of type {type(data)} to json, encountered error {e}"
        )
