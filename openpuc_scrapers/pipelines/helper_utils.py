import json
from typing import Any
from pydantic import BaseModel


from openpuc_scrapers.db.s3_utils import S3FileManager


# Helper functions
def save_to_disk_and_s3(path: str, bucket: str, content: str) -> None:
    S3FileManager(bucket).save_string_to_remote_file(path, content)


# FIXME: isnt working due to the higher order types sadly, also the last case can choke with recursive unjsonifiable types like RFCDatetimes and HttpUrl
def create_json_string(data: Any) -> str:
    if isinstance(data, dict):
        json_data = data
    elif isinstance(data, BaseModel):
        return data.model_dump_json()
    elif isinstance(data, list):
        json_data = [item.model_dump() for item in data]
    else:
        raise Exception("Data is not a list, dict, or BaseModel")
    return json.dumps(json_data, indent=2)


def save_json(path: str, bucket: str, data: Any) -> None:
    json_str = create_json_string(data)
    save_to_disk_and_s3(path, bucket, json_str)
