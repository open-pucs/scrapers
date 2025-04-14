import base64
import io
import os
from pathlib import Path
from typing import Tuple

from hashlib import blake2b

from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler
from typing import Any, Annotated


class Blake2bHash:
    """
    Represents a base64 encoded BLAKE2b hash

    A base64url-encoded BLAKE2b-256 hash
    Example: "_EYNhTcsAPjIT3iNNvTnY5KFC1wm61Mki_uBcb3yKv2zDncVYfdI6c_7tH_PAAS8IlhNaapBg21fwT4Z7Ttxig=="
    """

    def __init__(self, data: bytes = bytes(32)):
        if len(data) != 32:
            raise ValueError(f"Hash data must be 32 bytes, got {len(data)}")
        self.data = data

    def __str__(self) -> str:
        return base64.urlsafe_b64encode(self.data).decode("ascii")

    def __repr__(self) -> str:
        return f"KesslerHash({self.data!r})"

    def to_json(self) -> str:
        """Marshal the hash to a JSON string"""
        return f'"{str(self)}"'

    @classmethod
    def from_json(cls, json_data: bytes) -> "Blake2bHash":
        """Unmarshal a hash from JSON data"""
        if len(json_data) < 2 or json_data[0] != ord('"') or json_data[-1] != ord('"'):
            raise ValueError("Invalid JSON string")

        # Extract the string between quotes
        b64_str = json_data[1:-1].decode("ascii")
        return cls.from_string(b64_str)

    @classmethod
    def from_string(cls, s: str) -> "Blake2bHash":
        """Create a KesslerHash from a base64 encoded string"""
        try:
            decoded = base64.urlsafe_b64decode(s)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 string: {e}")

        if len(decoded) != 32:
            raise ValueError(f"Decoded base64 string length {len(decoded)} != 32")

        return cls(decoded)

    @classmethod
    def from_bytes(cls, b: bytes) -> "Blake2bHash":
        """Create a KesslerHash by hashing the provided bytes"""
        h = blake2b(b, digest_size=32)
        return cls(h.digest())

    @classmethod
    def from_file(cls, file_path: Path) -> "Blake2bHash":
        """Create a KesslerHash by hashing the contents of a file"""
        try:
            with open(file_path, "rb") as file:
                h = blake2b(digest_size=32)
                # Read and update hash in chunks to avoid loading large files into memory
                for chunk in iter(lambda: file.read(4096), b""):
                    h.update(chunk)
                return cls(h.digest())
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Provide a Pydantic core schema for Blake2bHash.

        This allows Pydantic to validate and serialize Blake2bHash instances
        using the from_string and __str__ methods.

        Args:
            _source_type: The source type being validated
            _handler: Pydantic's core schema handler

        Returns:
            A Pydantic core schema for Blake2bHash
        """
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    # Direct Blake2bHash instance
                    core_schema.is_instance_schema(cls),
                    # Convert from string
                    core_schema.no_info_plain_validator_function(cls.from_string),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x), return_schema=core_schema.str_schema()
            ),
        )


# # Type alias for easier type hinting
# Blake2bHashType = Annotated[
#     Blake2bHash, GetCoreSchemaHandler(Blake2bHash.__get_pydantic_core_schema__)
# ]
