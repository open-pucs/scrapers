from typing import Any
from pydantic import BaseModel
import json


class AirflowBaseModel(BaseModel):
    def serialize(self):
        # Deal with internal unserializeable types that airflow cant handle.
        return json.loads(self.model_dump_json())

    @staticmethod
    def deserialize(data: Any, version: int):
        return AirflowBaseModel(**data)
