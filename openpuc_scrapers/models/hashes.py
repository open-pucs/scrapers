from typing import Annotated, Union
import base64
from pathlib import Path
from hashlib import blake2b
from pydantic import (
    BaseModel,
    BeforeValidator,
    AfterValidator,
    PlainSerializer,
    WithJsonSchema,
    ValidationError,
    TypeAdapter,
)
import pydantic


def decode_blake2b(v: Union[str, bytes]):
    if isinstance(v, str):
        try:
            return base64.urlsafe_b64decode(v)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 string: {e}")
    elif isinstance(v, bytes):
        return v
    raise ValueError("Expected a string or bytes")


def validate_length(v: bytes):
    if len(v) != 32:
        raise ValueError(f"Expected 32 bytes, got {len(v)}")
    return v


Blake2bHash = Annotated[
    bytes,
    BeforeValidator(decode_blake2b),
    AfterValidator(validate_length),
    PlainSerializer(lambda x: base64.urlsafe_b64encode(x).decode("ascii")),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


def blake2b_hash_from_bytes(data: bytes) -> Blake2bHash:
    """Generate a Blake2bHash from the given bytes."""
    return blake2b(data, digest_size=32).digest()


def blake2b_hash_from_file(file_path: Path) -> Blake2bHash:
    """Generate a Blake2bHash from the contents of a file."""
    hasher = blake2b(digest_size=32)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.digest()
