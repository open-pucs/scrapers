use chrono::{DateTime, Utc};
use dokito_types::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};
use mycorrhiza_common::{
    file_extension::FileExtension,
    hash::Blake2bHash,
    s3_generic::{S3Credentials, cannonical_location::CannonicalS3ObjectLocation},
};
use non_empty_string::NonEmptyString;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::types::jurisdictions::JurisdictionInfo;

#[derive(Serialize, Deserialize, Debug, Clone, Copy, JsonSchema)]
pub enum AttachmentTextQuality {
    #[serde(rename = "low")]
    Low,
    #[serde(rename = "high")]
    High,
}
#[derive(Serialize, Deserialize, Debug, Clone, JsonSchema)]
pub struct RawAttachmentText {
    pub quality: AttachmentTextQuality,
    pub language: NonEmptyString,
    pub text: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawAttachment {
    pub hash: Blake2bHash,
    pub jurisdiction_info: JurisdictionInfo,
    pub name: NonEmptyString,
    pub extension: FileExtension,
    pub text_objects: Vec<RawAttachmentText>,
    pub date_added: chrono::DateTime<Utc>,
    pub date_updated: chrono::DateTime<Utc>,
    #[serde(default)]
    pub url: String,
    #[serde(default)]
    pub extra_metadata: HashMap<String, String>,
    #[serde(default)]
    pub file_size_bytes: u64,
}

impl CannonicalS3ObjectLocation for RawAttachment {
    type AddressInfo = Blake2bHash;

    fn generate_object_key(addr: &Self::AddressInfo) -> String {
        format!("raw/metadata/{addr}")
    }
    fn generate_bucket(_: &Self::AddressInfo) -> &'static str {
        &OPENSCRAPERS_S3_OBJECT_BUCKET
    }
    fn get_credentials(_: &Self::AddressInfo) -> &'static S3Credentials {
        &OPENSCRAPERS_S3
    }
}
