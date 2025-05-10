import os
import base64
import pytest
from pydantic import TypeAdapter
from .hashes import (
    blake2b_hash_from_bytes,
    blake2b_to_str,
    Blake2bHash,
)

def test_blake2b_roundtrip():
    """
    Test that random 32-byte hashes round-trip through base64 encoding and decoding correctly.
    """
    adapter = TypeAdapter(Blake2bHash)
    for _ in range(1000):
        original = os.urandom(32)
        s = blake2b_to_str(original)
        decoded = adapter.validate_python(s)
        assert decoded == original


def test_blake2b_hash_validity():
    """
    Test that blake2b_hash_from_bytes produces expected hex digests for known inputs.
    """
    # Test case 1
    input1 = b"The quick brown fox jumped over the lazy dog"
    expected_hex1 = "cd1c3b120f8d0af28a9b6b1c43da5aba4be633ac0a303719f6dfa5ee1890f28d"
    h1 = blake2b_hash_from_bytes(input1)
    assert h1.hex() == expected_hex1

    # Test case 2
    input2 = b"the mitochondria is the powerhouse of a cell"
    expected_hex2 = "821435d2a2b379ad2e4bb11c41c0b2ec2cf2135f09b0afa740d5efc2818778f7"
    h2 = blake2b_hash_from_bytes(input2)
    assert h2.hex() == expected_hex2
