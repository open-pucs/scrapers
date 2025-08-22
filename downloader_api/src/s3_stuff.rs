use std::path::Path;

use anyhow::anyhow;
use futures_util::join;
use non_empty_string::non_empty_string;
use tracing::{debug, error, info};

use crate::common::hash::Blake2bHash;
use crate::common::s3_generic::fetchers_and_getters::{
    download_s3_bytes, download_s3_json, match_all_with_prefix, upload_s3_bytes, upload_s3_json,
};
use crate::types::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};
use crate::types::jurisdictions::JurisdictionInfo;
use crate::types::raw::{RawAttachment, RawGenericCase};
use crate::types::s3_uri::S3Location;
use aws_sdk_s3::{Client as S3Client, primitives::ByteStream};

pub fn get_raw_attach_obj_key(hash: Blake2bHash) -> String {
    let key = format!("raw/metadata/{hash}.json");
    debug!(%hash, "Generated raw attachment object key: {}", key);
    key
}

pub fn get_raw_attach_file_key(hash: Blake2bHash) -> String {
    let key = format!("raw/file/{hash}");
    debug!(%hash, "Generated raw attachment file key: {}", key);
    key
}

pub fn generate_s3_object_uri_from_key(key: &str) -> String {
    let uri = S3Location::default_from_key(key).to_string();
    debug!(key, "Generated S3 object URI: {}", uri);
    uri
}
pub async fn make_s3_client() -> S3Client {
    info!("Creating S3 client");
    OPENSCRAPERS_S3.make_s3_client().await
}

pub async fn fetch_attachment_data_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<RawAttachment> {
    info!(%hash, "Fetching attachment data from S3");
    let key = get_raw_attach_obj_key(hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    download_s3_json(s3_client, bucket, &key)
}

pub async fn fetch_attachment_file_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<Vec<u8>> {
    info!(%hash, "Fetching attachment file from S3");
    let key = get_raw_attach_file_key(hash);
    download_s3_bytes(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key).await
}

pub async fn fetch_attachment_file_from_s3_with_filename(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<(String, Vec<u8>)> {
    info!(%hash, "Fetching attachment file from S3");
    let key = get_raw_attach_file_key(hash);
    let bytes_future = download_s3_bytes(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key);
    let metadata_future = fetch_attachment_data_from_s3(s3_client, hash);
    let (Ok(bytes), metadata) = join!(bytes_future, metadata_future) else {
        return Err(anyhow!("fetching bytes failed."));
    };

    let filename = metadata
        .ok()
        .map(|v| v.name + "." + &v.extension.to_string())
        .unwrap_or_else(|| non_empty_string!("unknown_filename.pdf"));
    Ok((filename.to_string(), bytes))
}
pub fn get_case_s3_key(case_name: &str, jurisdiction: &JurisdictionInfo) -> String {
    let country = &*jurisdiction.country;
    let state = &*jurisdiction.state;
    let jurisdiction_name = &*jurisdiction.jurisdiction;
    let key = format!("objects/{country}/{state}/{jurisdiction_name}/{case_name}.json");
    debug!(
        case_name,
        jurisdiction_name, state, country, "Generated case S3 key: {}", key
    );
    key
}
pub fn get_jurisdiction_prefix(jurisdiction: &JurisdictionInfo) -> String {
    let country = &*jurisdiction.country;
    let state = &*jurisdiction.state;
    let jurisdiction_name = &*jurisdiction.jurisdiction;
    let key = format!("objects/{country}/{state}/{jurisdiction_name}");
    key
}

pub async fn does_openscrapers_attachment_exist(s3_client: &S3Client, hash: Blake2bHash) -> bool {
    info!(%hash, "Checking if attachment exists in S3");
    let obj_key = get_raw_attach_obj_key(hash);
    let file_key = get_raw_attach_file_key(hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    debug!(
        "Checking for attachment with object key: {} and file key: {}",
        obj_key, file_key
    );

    let obj_exists = s3_client
        .head_object()
        .bucket(bucket)
        .key(obj_key)
        .send()
        .await;

    let file_exists = s3_client
        .head_object()
        .bucket(bucket)
        .key(file_key)
        .send()
        .await;

    let result = obj_exists.is_ok() && file_exists.is_ok();
    info!("Attachment exists: {}", result);
    result
}

pub async fn fetch_case_filing_from_s3(
    s3_client: &S3Client,
    case_name: &str,
    jurisdiction: &JurisdictionInfo,
) -> anyhow::Result<RawGenericCase> {
    let key = get_case_s3_key(case_name, jurisdiction);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    info!("Successfully pushed case to S3");
    download_s3_json(s3_client, bucket, &key).await
}

pub async fn push_case_to_s3(
    s3_client: &S3Client,
    case: &RawGenericCase,
    jurisdiction: &JurisdictionInfo,
) -> anyhow::Result<()> {
    info!(case_number = %case.case_govid, "Pushing case to S3 and DB");
    let key = get_case_s3_key(case.case_govid.as_ref(), jurisdiction);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    info!("Successfully pushed case to S3");
    upload_s3_json(s3_client, bucket, &key, case).await
}

pub async fn list_cases_for_jurisdiction(
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
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let prefix = format!("objects/{country}/{state}/{jurisdiction}/");
    let mut case_names = Vec::new();
    info!("Listing cases with prefix: {}", prefix);
    let matches = match_all_with_prefix(s3_client, bucket, &prefix).await?;
    for val in matches.iter_mut() {
        if let Some(stripped) = val.strip_suffix(".json") {
            *val = stripped.to_string();
        };
    }
}

pub async fn push_raw_attach_file_to_s3(
    s3_client: &S3Client,
    raw_att: &RawAttachment,
    file_contents: Vec<u8>,
) -> anyhow::Result<()> {
    info!(hash = %raw_att.hash, "Pushing raw attachment file to S3");
    let file_key = get_raw_attach_file_key(raw_att.hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;

    upload_s3_bytes(s3_client, bucket, &file_key, file_contents).await?;
    info!("Successfully pushed file to S3");

    Ok(())
}

pub async fn push_raw_attach_object_to_s3(
    s3_client: &S3Client,
    raw_att: &RawAttachment,
) -> anyhow::Result<()> {
    info!(hash = %raw_att.hash, "Pushing raw attachment file to S3");
    let obj_key = get_raw_attach_obj_key(raw_att.hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;

    upload_s3_json(s3_client, bucket, &obj_key, raw_att).await?;
    info!("Successfully pushed metadata object to S3");

    Ok(())
}
