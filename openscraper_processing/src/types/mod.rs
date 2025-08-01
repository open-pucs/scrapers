use chrono::{DateTime, Utc};
use file_extension::FileExtension;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::types::hash::Blake2bHash;

pub mod env_vars;
pub mod file_extension;
pub mod hash;
pub mod pagination;
pub mod s3_uri;

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct JurisdictionInfo {
    pub country: String,
    pub state: String,
    pub jurisdiction: String,
}
impl Default for JurisdictionInfo {
    fn default() -> Self {
        let unknown_static = "unknown";
        JurisdictionInfo {
            country: unknown_static.to_string(),
            state: unknown_static.to_string(),
            jurisdiction: unknown_static.to_string(),
        }
    }
}

impl JurisdictionInfo {
    pub fn new_usa(jurisdiction: &str, state: &str) -> Self {
        JurisdictionInfo {
            country: "usa".to_string(),
            state: state.to_string(),
            jurisdiction: jurisdiction.to_string(),
        }
    }
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct CaseWithJurisdiction {
    pub case: GenericCase,
    pub jurisdiction: JurisdictionInfo,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct GenericAttachment {
    pub name: String,
    pub url: String,
    pub document_extension: Option<String>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
    pub hash: Option<Blake2bHash>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone, Default)]
pub struct GenericFiling {
    pub name: String,
    pub filed_date: DateTime<Utc>,
    pub party_name: String,
    pub filing_type: String,
    pub description: String,
    pub attachments: Vec<GenericAttachment>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone, Default)]
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

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawAttachment {
    pub hash: Blake2bHash,
    pub jurisdiction_info: JurisdictionInfo,
    pub name: String,
    pub extension: FileExtension,
    pub text_objects: Vec<RawAttachmentText>,
    pub date_added: chrono::DateTime<Utc>,
    pub date_updated: chrono::DateTime<Utc>,
}
