use std::collections::HashMap;

use chrono::{DateTime, NaiveDate, Utc};
use mycorrhiza_common::{file_extension::FileExtension, hash::Blake2bHash};
use non_empty_string::NonEmptyString;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::raw::{GenericParty, RawGenericAttachment};

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct ProcessedGenericAttachment {
    pub name: String,
    pub document_extension: FileExtension,
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
pub struct ProcessedGenericFiling {
    pub filed_date: NaiveDate,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub organization_authors: Vec<NonEmptyString>,
    #[serde(default)]
    pub individual_authors: Vec<NonEmptyString>,
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
pub struct RawGenericCase {
    pub case_govid: NonEmptyString,
    // This shouldnt be an optional field in the final submission, since it can be calculated from
    // the minimum of the fillings, and the scraper should calculate it.
    #[serde(default)]
    pub opened_date: NaiveDate,
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
    pub filings: Vec<ProcessedGenericFiling>,
    #[serde(default)]
    pub case_parties: Vec<GenericParty>,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
    #[serde(default = "Utc::now")]
    pub indexed_at: DateTime<Utc>,
}
