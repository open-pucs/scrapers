use base64::{Engine, engine::general_purpose::URL_SAFE};
use blake2::{Blake2b, Digest};
use serde::{Deserialize, Deserializer, Serialize, Serializer, de};
use std::borrow::Cow;
use std::fmt;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use std::str::FromStr;
use thiserror::Error;

use schemars::{JsonSchema, Schema, json_schema};

/// Represents a base64 URL-encoded BLAKE2b-256 hash
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Blake2bHash([u8; 32]);

impl Blake2bHash {
    /// Creates hash from raw bytes
    pub fn from_bytes(data: &[u8]) -> Self {
        let mut hasher = Blake2b::<blake2::digest::consts::U32>::new();
        hasher.update(data);
        Blake2bHash(hasher.finalize().into())
    }

    /// Creates hash from file contents
    pub fn from_file<P: AsRef<Path>>(path: P) -> io::Result<Self> {
        let mut file = File::open(path)?;
        let mut hasher = Blake2b::<blake2::digest::consts::U32>::new();
        let mut buffer = [0; 4096];

        loop {
            let count = file.read(&mut buffer)?;
            if count == 0 {
                break;
            }
            hasher.update(&buffer[..count]);
        }

        Ok(Blake2bHash(hasher.finalize().into()))
    }

    pub const fn peek_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Display for Blake2bHash {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", URL_SAFE.encode(self.0))
    }
}

#[derive(Error, Debug)]
pub enum Blake2bHashDecodeError {
    #[error("Base64 decoding failed: {0}")]
    Base64DecodingFailed(#[from] base64::DecodeError),
    #[error("Decoded base64 length {0} != 32")]
    InvalidLength(usize),
}

impl FromStr for Blake2bHash {
    type Err = Blake2bHashDecodeError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let bytes = URL_SAFE.decode(s)?;

        if bytes.len() != 32 {
            return Err(Blake2bHashDecodeError::InvalidLength(bytes.len()));
        }

        let mut hash = [0u8; 32];
        hash.copy_from_slice(&bytes);
        Ok(Blake2bHash(hash))
    }
}

impl Serialize for Blake2bHash {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

impl<'de> Deserialize<'de> for Blake2bHash {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        s.parse().map_err(de::Error::custom)
    }
}

impl JsonSchema for Blake2bHash {
    fn schema_name() -> Cow<'static, str> {
        Cow::Borrowed("Blake2bHash")
    }

    fn json_schema(_: &mut schemars::SchemaGenerator) -> Schema {
        json_schema!({
        "type": "string",
        "pattern": "^[a-zA-Z0-9_-]{43}$",
        "title": "Base64 URL-encoded BLAKE2b-256 hash",
        "description": "String representation of a BLAKE2b-256 hash using URL-safe base64 encoding without padding"
        })
    }
}
#[cfg(test)]
mod tests {

    use rand::Rng;

    use super::*;

    use hex;
    #[test]
    fn test_kessler_hash_round_trip() {
        let mut rng = rand::rng();
        for _ in 0..1000 {
            // Generate random hash
            let to_be_hashed: [u8; 64] = rng.random();
            let original = Blake2bHash::from_bytes(&to_be_hashed);

            // Convert to base64 string
            let s = original.to_string();

            // Convert back from string
            let decoded = match s.parse::<Blake2bHash>() {
                Ok(h) => h,
                Err(e) => panic!("Error decoding string: {e}"),
            };

            // Verify match
            assert_eq!(original, decoded, "Round-trip hash mismatch");
        }
    }

    #[test]
    fn test_kessler_hash_validity() {
        // Helper function for testing
        fn test_expected_hash(data: &[u8], expected_hex: &str) -> Result<(), String> {
            let computed_hash = Blake2bHash::from_bytes(data);
            let computed_hash_bytes = *computed_hash.peek_bytes();
            let expected_bytes = hex::decode(expected_hex)
                .map_err(|e| format!("Failed to decode hex string: {e}"))?;

            if expected_bytes.len() != 32 {
                return Err("Expected hash length must be 32 bytes".into());
            }

            let expected_hash_bytes: [u8; 32] = expected_bytes
                .try_into()
                .map_err(|_| "Conversion to array failed".to_string())?;

            if computed_hash_bytes == expected_hash_bytes {
                Ok(())
            } else {
                Err(format!(
                    "Hash mismatch\nExpected:{expected_hash_bytes:?}\nGot:{computed_hash_bytes:?}"
                ))
            }
        }

        // Test cases
        let test_cases = [
            (
                b"The quick brown fox jumped over the lazy dog",
                "cd1c3b120f8d0af28a9b6b1c43da5aba4be633ac0a303719f6dfa5ee1890f28d",
            ),
            (
                b"the mitochondria is the powerhouse of a cell",
                "821435d2a2b379ad2e4bb11c41c0b2ec2cf2135f09b0afa740d5efc2818778f7",
            ),
        ];

        for (input, expected_hex) in test_cases {
            test_expected_hash(input, expected_hex).unwrap_or_else(|e| panic!("Test failed: {e}"));
        }
    }
}
