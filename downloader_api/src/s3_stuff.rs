use anyhow::anyhow;
use futures_util::join;
use mycorrhiza_common::s3_generic::fetchers_and_getters::{S3Addr, S3DirectoryAddr};
use mycorrhiza_common::s3_generic::s3_uri::S3LocationWithCredentials;
use non_empty_string::non_empty_string;
use tracing::{debug, info};

use crate::types::attachments::RawAttachment;
use crate::types::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};
use crate::types::jurisdictions::JurisdictionInfo;
use aws_sdk_s3::Client as S3Client;
use mycorrhiza_common::hash::Blake2bHash;

pub fn get_raw_attach_file_key(hash: Blake2bHash) -> String {
    let key = format!("raw/file/{hash}");
    debug!(%hash, "Generated raw attachment file key: {}", key);
    key
}

pub fn generate_s3_object_uri_from_key(key: &str) -> String {
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let credentials = &*OPENSCRAPERS_S3;
    let uri = S3LocationWithCredentials::from_key_bucket_and_credentials(key, bucket, credentials)
        .to_string();
    debug!(key, "Generated S3 object URI: {}", uri);
    uri
}
pub async fn make_s3_client() -> S3Client {
    OPENSCRAPERS_S3.make_s3_client().await
}

// Fetching stuff for attachments, seperate from all the other object stuff

pub async fn fetch_attachment_file_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<Vec<u8>> {
    info!(%hash, "Fetching attachment file from S3");
    let key = get_raw_attach_file_key(hash);
    S3Addr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key)
        .download_bytes()
        .await
}

pub fn get_jurisdiction_prefix(jurisdiction: &JurisdictionInfo) -> String {
    let country = &*jurisdiction.country;
    let state = &*jurisdiction.state;
    let jurisdiction_name = &*jurisdiction.jurisdiction;
    let key = format!("objects/{country}/{state}/{jurisdiction_name}");
    key
}

pub async fn list_processed_cases_for_jurisdiction(
    s3_client: &S3Client,
    JurisdictionInfo {
        jurisdiction,
        state,
        country,
    }: &JurisdictionInfo,
) -> anyhow::Result<Vec<String>> {
    info!(
        jurisdiction,
        state, country, "Listing cases for jurisdiction"
    );
    let prefix = format!("objects/{country}/{state}/{jurisdiction}/");
    info!("Listing cases with prefix: {}", prefix);
    let mut matches = S3DirectoryAddr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &prefix)
        .list_all()
        .await?;
    for val in matches.iter_mut() {
        if let Some(stripped_json) = val.strip_suffix(".json")
            && let Some(stripped) = stripped_json.strip_prefix(&prefix)
        {
            *val = stripped.to_string();
        };
    }
    Ok(matches)
}

pub async fn list_raw_cases_for_jurisdiction(
    s3_client: &S3Client,
    JurisdictionInfo {
        jurisdiction,
        state,
        country,
    }: &JurisdictionInfo,
) -> anyhow::Result<Vec<String>> {
    info!(
        jurisdiction,
        state, country, "Listing cases for jurisdiction"
    );
    let prefix = format!("objects_raw/{country}/{state}/{jurisdiction}/");
    info!("Listing cases with prefix: {}", prefix);
    let mut matches = S3DirectoryAddr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &prefix)
        .list_all()
        .await?;
    for val in matches.iter_mut() {
        if let Some(stripped_json) = val.strip_suffix(".json")
            && let Some(stripped) = stripped_json.strip_prefix(&prefix)
        {
            *val = stripped.to_string();
        };
    }
    Ok(matches)
}

pub async fn push_raw_attach_file_to_s3(
    s3_client: &S3Client,
    raw_att: &RawAttachment,
    file_contents: Vec<u8>,
) -> anyhow::Result<()> {
    info!(hash = %raw_att.hash, "Pushing raw attachment file to S3");
    let file_key = get_raw_attach_file_key(raw_att.hash);

    S3Addr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &file_key)
        .upload_bytes(file_contents)
        .await?;
    debug!("Successfully pushed file to S3");

    Ok(())
}
