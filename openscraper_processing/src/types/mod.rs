use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub mod hash;

#[derive(Serialize, Deserialize, Debug)]
pub struct GenericAttachment {
    pub name: String,
    pub url: String,
    pub document_extension: Option<String>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
    pub hash: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct GenericFiling {
    pub name: String,
    pub filed_date: DateTime<Utc>,
    pub party_name: String,
    pub filing_type: String,
    pub description: String,
    pub attachments: Vec<GenericAttachment>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
}

#[derive(Serialize, Deserialize, Debug)]
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
    pub filings: Option<Vec<GenericFiling>>,
    pub extra_metadata: HashMap<String, serde_json::Value>,
    pub indexed_at: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug, Clone, Copy)]
pub enum AttachmentTextQuality {
    #[serde(rename = "low")]
    Low,
    #[serde(rename = "high")]
    High,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct RawAttachmentText {
    pub quality: AttachmentTextQuality,
    pub language: String,
    pub text: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct RawAttachment {
    pub hash: String,
    pub name: String,
    pub extension: String,
    pub text_objects: Vec<RawAttachmentText>,
}
