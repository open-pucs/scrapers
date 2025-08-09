use std::fmt;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use super::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct S3Location {
    pub key: String,
    pub bucket: String,
    pub endpoint: String,
    pub region: String,
}

impl S3Location {
    pub fn default_from_key(key: &str) -> Self {
        S3Location {
            key: key.to_owned(),
            bucket: (*OPENSCRAPERS_S3_OBJECT_BUCKET).clone(),
            endpoint: OPENSCRAPERS_S3.endpoint.clone(),
            region: OPENSCRAPERS_S3.cloud_region.clone(),
        }
    }
}
// https://examplebucket.sfo3.digitaloceanspaces.com/this/is/the/file/key
//
// For this example the
// bucket: examplebucket
// region: sfo3
// endpoint: https://sfo3.digitaloceanspaces.com
// key: this/is/the/file/key
impl fmt::Display for S3Location {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // strip off the "https://" prefix on the endpoint to get e.g. "sfo3.digitaloceanspaces.com"
        let host_part = self
            .endpoint
            .strip_prefix("https://")
            .unwrap_or(&self.endpoint);

        // make sure we don’t end up with duplicate or missing slashes
        let key_part = self.key.trim_start_matches('/');

        // build "https://{bucket}.{host_part}/{key…}"
        let mut url = format!("https://{}.{}", self.bucket, host_part);
        if !key_part.is_empty() {
            url.push('/');
            url.push_str(key_part);
        }
        write!(f, "{url}")
    }
}

//
// Try to parse the URL back into its components.
// Expects URLs of the form
//   "https://{bucket}.{region}.{rest…}/{key…}"
//
#[derive(Error, Debug)]
pub enum S3DecodeError {
    #[error("Invalid file location for File")]
    InvalidLocation,
}
impl TryFrom<String> for S3Location {
    type Error = S3DecodeError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        // 1) strip the scheme
        let without_scheme = value
            .strip_prefix("https://")
            .ok_or(S3DecodeError::InvalidLocation)?;

        // 2) split into host vs. path
        //    e.g. "examplebucket.sfo3.digitaloceanspaces.com/this/is/…"
        let mut split = without_scheme.splitn(2, '/');
        let host = split.next().unwrap();
        let key = split.next().unwrap_or("").to_string();

        // 3) break host into bucket, region, and the rest of the domain
        //    host_parts = ["examplebucket", "sfo3", "digitaloceanspaces.com"]
        let host_parts: Vec<&str> = host.split('.').collect();
        if host_parts.len() < 3 {
            return Err(S3DecodeError::InvalidLocation);
        }
        let bucket = host_parts[0].to_string();
        let region = host_parts[1].to_string();
        let domain_rest = host_parts[2..].join(".");

        // 4) rebuild the endpoint (scheme + region + rest-of-domain)
        let endpoint = format!("https://{region}.{domain_rest}");

        Ok(S3Location {
            key,
            bucket,
            region,
            endpoint,
        })
    }
}
