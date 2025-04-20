import json
from typing import Any
from pydantic import BaseModel


from openpuc_scrapers.db.s3_utils import S3FileManager


# Helper functions
def save_to_disk_and_s3(path: str, bucket: str, content: str) -> None:
    S3FileManager(bucket).save_string_to_remote_file(path, content)


# Takes in a dict, a pydantic BaseModel, or a List[BaseModel]
def create_json_string(data) -> str:
    def _serialize(obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        return obj

    if isinstance(data, BaseModel):
        return data.model_dump_json(indent=2)

    if isinstance(data, list):
        return json.dumps([_serialize(item) for item in data], indent=2)

    if isinstance(data, dict):
        return json.dumps({k: _serialize(v) for k, v in data.items()}, indent=2)

    raise ValueError(f"Unsupported data type: {type(data)}")


def save_json(path: str, bucket: str, data: Any) -> None:
    json_str = create_json_string(data)
    save_to_disk_and_s3(path, bucket, json_str)
