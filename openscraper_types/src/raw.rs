#![warn(unused_extern_crates)]
use chrono::{DateTime, NaiveDate, Utc};
use non_empty_string::NonEmptyString;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_with::{DefaultOnError, serde_as};
use std::collections::HashMap;

use crate::jurisdictions::JurisdictionInfo;

use mycorrhiza_common::{file_extension::FileExtension, hash::Blake2bHash};

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawDocketWithJurisdiction {
    pub docket: RawGenericDocket,
    pub jurisdiction: JurisdictionInfo,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone, Copy, Default)]
#[serde(rename_all = "snake_case")]
pub enum RawArtificalPersonType {
    #[default]
    Unknown,
    Human,
    Organization,
}

#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericParty {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub artifical_person_type: RawArtificalPersonType,
    #[serde(default)]
    pub western_human_first_name: String,
    #[serde(default)]
    pub western_human_last_name: String,
    #[serde(default)]
    pub human_title: String,
    #[serde(default)]
    pub human_associated_company: String,
    #[serde(default)]
    pub contact_email: String,
    #[serde(default)]
    pub contact_phone: String,
    #[serde(default)]
    pub contact_address: String,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
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

use serde::Deserializer;

fn deserialize_date_only<'de, D>(deserializer: D) -> Result<Option<NaiveDate>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: Option<String> = Option::deserialize(deserializer)?;
    if let Some(s) = s {
        // First, try parsing just the date
        if let Ok(date) = NaiveDate::parse_from_str(&s, "%Y-%m-%d") {
            return Ok(Some(date));
        }
        // Next, try parsing as full datetime and truncate
        if let Ok(dt) = DateTime::parse_from_rfc3339(&s) {
            return Ok(Some(dt.date_naive()));
        }
        // return Err(serde::de::Error::custom(format!("Invalid date: {}", s)));
        return Ok(None);
    }
    Ok(None)
}
#[serde_as]
#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericFiling {
    #[serde(default, deserialize_with = "deserialize_date_only")]
    pub filed_date: Option<NaiveDate>,
    #[serde(default)]
    pub filling_govid: String,
    #[serde(default)]
    pub filling_url: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub organization_authors: Vec<String>,
    #[serde(default)]
    pub individual_authors: Vec<String>,
    #[serde(default)]
    pub organization_authors_blob: String,
    #[serde(default)]
    pub individual_authors_blob: String,
    #[serde(default)]
    pub filing_type: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub attachments: Vec<RawGenericAttachment>,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
}

#[serde_as]
#[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
pub struct RawGenericDocket {
    pub case_govid: NonEmptyString,
    // This shouldnt be an optional field in the final submission, since it can be calculated from
    // the minimum of the fillings, and the scraper should calculate it.
    #[serde(default, deserialize_with = "deserialize_date_only")]
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
    pub case_parties: Vec<RawGenericParty>,
    #[serde(default)]
    pub extra_metadata: HashMap<String, serde_json::Value>,
    #[serde(default = "Utc::now")]
    pub indexed_at: DateTime<Utc>,
}
