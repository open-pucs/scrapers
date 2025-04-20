import json
from typing import Any
from pydantic import BaseModel


from openpuc_scrapers.db.s3_utils import S3FileManager


# Helper functions
def save_to_disk_and_s3(path: str, bucket: str, content: str) -> None:
    S3FileManager(bucket).save_string_to_remote_file(path, content)


# isnt working due to the higher order types sadly
# def save_json(path: str, data: BaseModel | List[BaseModel]) -> None:
def save_json(path: str, bucket: str, data: Any) -> None:
    if isinstance(data, dict):
        json_data = data
    elif isinstance(data, BaseModel):
        json_data = data.model_dump()
    elif isinstance(data, list):
        json_data = [item.model_dump() for item in data]
    else:
        raise Exception("Data is not a list, dict, or BaseModel")
    json_str = json.dumps(json_data, indent=2)
    save_to_disk_and_s3(path, bucket, json_str)
