use chrono::{DateTime, NaiveDate, Utc};
use non_empty_string::NonEmptyString;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::types::jurisdictions::JurisdictionInfo;
use mycorrhiza_common::{file_extension::FileExtension, hash::Blake2bHash};

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawCaseWithJurisdiction {
    pub case: RawGenericDocket,
    pub jurisdiction: JurisdictionInfo,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericAttachment {
    pub name: String,
    pub document_extension: FileExtension,
    #[serde(default)]
    pub attachment_govid: String,
    #[serde(default)]
    pub url: String,
    #[serde(default)]
    pub attachment_type: String,
    #[serde(default)]
    pub attachment_subtype: String,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub hash: Option<Blake2bHash>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericFiling {
    pub filed_date: Option<NaiveDate>,
    #[serde(default)]
    pub filling_govid: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub organization_authors: Vec<String>,
    #[serde(default)]
    pub individual_authors: Vec<String>,
    #[serde(default)]
    pub filing_type: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub attachments: Vec<RawGenericAttachment>,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericDocket {
    pub case_govid: NonEmptyString,
    // This shouldnt be an optional field in the final submission, since it can be calculated from
    // the minimum of the fillings, and the scraper should calculate it.
    #[serde(default)]
    pub opened_date: Option<NaiveDate>,
    #[serde(default)]
    pub case_name: String,
    #[serde(default)]
    pub case_url: String,
    #[serde(default)]
    pub case_type: String,
    #[serde(default)]
    pub case_subtype: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub industry: String,
    #[serde(default)]
    pub petitioner: String,
    #[serde(default)]
    pub hearing_officer: String,
    #[serde(default)]
    pub closed_date: Option<NaiveDate>,
    #[serde(default)]
    pub filings: Vec<RawGenericFiling>,
    #[serde(default)]
    pub case_parties: Vec<GenericParty>,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
    #[serde(default = "Utc::now")]
    pub indexed_at: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct GenericParty {
    name: NonEmptyString,
    is_corperate_entity: bool,
    is_human: bool,
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
