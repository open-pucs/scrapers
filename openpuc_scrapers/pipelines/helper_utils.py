import asyncio
import json
import logging
from typing import Any, Optional
from pydantic import BaseModel
import requests

from openpuc_scrapers.models.constants import OPENSCRAPERS_INTERNAL_API_URL


default_logger = logging.getLogger(__name__)


class JsonS3File(BaseModel):
    key: str
    bucket: Optional[str]
    contents: Any


def save_json_sync(path: str, data: Any, bucket: Optional[str] = None) -> None:
    try:
        url = f"{OPENSCRAPERS_INTERNAL_API_URL}/admin/write_openscrapers_s3_json"
        # json_str = create_json_string(data)
        # json_obj = json.loads(json_str)
        # payload = {"key": path, "contents": json_obj}
        # if bucket is not None:
        #     payload["bucket"] = bucket
        # response = requests.post(url, json=payload)
        payload = JsonS3File(key=path, bucket=bucket, contents=data)
        payload_str = payload.model_dump_json()
        response = requests.post(url, data=payload_str)
        response.raise_for_status()
    except Exception as e:
        default_logger.error(
            f"Could not convert data of type {type(data)} to json, encountered error {e}"
        )


# def create_json_string(data: Any) -> str:
#     def _serialize(obj):
#         if isinstance(obj, BaseModel):
#             return obj.model_dump(mode="json")
#             # return json.loads(obj.model_dump_json())
#         return obj
#
#     if isinstance(data, BaseModel):
#         return data.model_dump_json(indent=2)
#
#     if isinstance(data, list):
#         return json.dumps([_serialize(item) for item in data], indent=2)
#
#     if isinstance(data, dict):
#         return json.dumps({k: _serialize(v) for k, v in data.items()}, indent=2)
#
#     raise ValueError(f"Unsupported data type: {type(data)}")
#
#
