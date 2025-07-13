use chrono::{DateTime, Utc};
use file_extension::FileExtension;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::types::hash::Blake2bHash;

pub mod env_vars;
pub mod file_extension;
pub mod hash;
pub mod s3_uri;

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct GenericAttachment {
    pub name: String,
    pub url: String,
    pub document_extension: Option<String>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
    pub hash: Option<Blake2bHash>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct GenericFiling {
    pub name: String,
    pub filed_date: DateTime<Utc>,
    pub party_name: String,
    pub filing_type: String,
    pub description: String,
    pub attachments: Vec<GenericAttachment>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct GenericCase {
    pub case_number: String,
    pub case_name: String,
    pub case_url: String,
    pub case_type: Option<String>,
    pub description: Option<String>,
    pub industry: Option<String>,
    pub petitioner: Option<String>,
    pub hearing_officer: Option<String>,
    pub opened_date: Option<DateTime<Utc>>,
    pub closed_date: Option<DateTime<Utc>>,
    pub filings: Vec<GenericFiling>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
    pub indexed_at: DateTime<Utc>,
}

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
    pub language: String,
    pub text: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema)]
pub struct RawAttachment {
    pub hash: Blake2bHash,
    pub name: String,
    pub extension: FileExtension,
    pub text_objects: Vec<RawAttachmentText>,
}
