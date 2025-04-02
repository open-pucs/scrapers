import base64
import io
import os
from typing import Tuple

from hashlib import blake2b


class KesslerHash:
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
    def from_json(cls, json_data: bytes) -> "KesslerHash":
        """Unmarshal a hash from JSON data"""
        if len(json_data) < 2 or json_data[0] != ord('"') or json_data[-1] != ord('"'):
            raise ValueError("Invalid JSON string")

        # Extract the string between quotes
        b64_str = json_data[1:-1].decode("ascii")
        return cls.from_string(b64_str)

    @classmethod
    def from_string(cls, s: str) -> "KesslerHash":
        """Create a KesslerHash from a base64 encoded string"""
        try:
            decoded = base64.urlsafe_b64decode(s)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 string: {e}")

        if len(decoded) != 32:
            raise ValueError(f"Decoded base64 string length {len(decoded)} != 32")

        return cls(decoded)

    @classmethod
    def from_bytes(cls, b: bytes) -> "KesslerHash":
        """Create a KesslerHash by hashing the provided bytes"""
        h = blake2b(b, digest_size=32)
        return cls(h.digest())

    @classmethod
    def from_file(cls, file_path: str) -> "KesslerHash":
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
