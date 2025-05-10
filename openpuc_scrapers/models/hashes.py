from hashlib import blake2b
from typing import Annotated, Union
import base64
from pathlib import Path
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


def blake2b_to_str(v: bytes) -> str:
    return base64.urlsafe_b64encode(v).decode("ascii")


Blake2bHash = Annotated[
    bytes,
    BeforeValidator(decode_blake2b),
    AfterValidator(validate_length),
    PlainSerializer(blake2b_to_str),
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


# func TestKesslerHashRoundTrip(t *testing.T) {
# 	for i := 0; i < 1000; i++ {
# 		// Generate random 32-byte KesslerHash
# 		// Or better, fill with random bytes:
# 		original := hashes.KesslerHash{}
# 		rand.Read(original[:])
#
# 		// Convert to base64 string
# 		s := original.String()
#
# 		// Convert back from string
# 		decoded, err := hashes.HashFromString(s)
# 		if err != nil {
# 			t.Errorf("Error decoding string on iteration %d: %v", i, err)
# 			continue
# 		}
#
# 		// Verify decoded hash matches original
# 		if original != decoded {
# 			t.Errorf("Decoded hash does not match original on iteration %d", i)
# 		}
# 	}
# }
# func TestKesslerHashValidity(t *testing.T) {
# 	input := []byte("The quick brown fox jumped over the lazy dog")
# 	expectedHex := "cd1c3b120f8d0af28a9b6b1c43da5aba4be633ac0a303719f6dfa5ee1890f28d"
# 	err := hashes.TestExpectedHash(input, expectedHex)
# 	if err != nil {
# 		t.Fatalf("Hash did not match for input %v: %v", input, err)
# 	}
# 	input = []byte("the mitochondria is the powerhouse of a cell")
# 	expectedHex = "821435d2a2b379ad2e4bb11c41c0b2ec2cf2135f09b0afa740d5efc2818778f7"
# 	err = hashes.TestExpectedHash(input, expectedHex)
# 	if err != nil {
# 		t.Fatalf("Hash did not match for input %v: %v", input, err)
# 	}
# }
