use chrono::{DateTime, Utc};
use mycorrhiza_common::{file_extension::FileExtension, hash::Blake2bHash};
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
