use std::path::Path;
use std::time::Duration;

use anyhow::{anyhow, bail};
use aws_config::{BehaviorVersion, Region};
use aws_sdk_s3::config::Credentials;
use chrono::offset;
use tracing::{debug, error, info};

use crate::types::JurisdictionInfo;
use crate::types::s3_uri::S3Location;
use crate::types::{
    GenericCase, RawAttachment,
    env_vars::{
        OPENSCRAPERS_S3_ACCESS_KEY, OPENSCRAPERS_S3_CLOUD_REGION, OPENSCRAPERS_S3_ENDPOINT,
        OPENSCRAPERS_S3_OBJECT_BUCKET, OPENSCRAPERS_S3_SECRET_KEY,
    },
    hash::Blake2bHash,
};
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
    let region = Region::new(&**OPENSCRAPERS_S3_CLOUD_REGION);
    let creds = Credentials::new(
        &**OPENSCRAPERS_S3_ACCESS_KEY,
        &**OPENSCRAPERS_S3_SECRET_KEY,
        None, // no session token
        None, // no expiration
        "manual",
    );

    // Start from the env-loader so we still pick up other settings (timeouts, retry, etc)
    let cfg_loader = aws_config::defaults(BehaviorVersion::latest())
        .region(region)
        .credentials_provider(creds)
        .endpoint_url(&**OPENSCRAPERS_S3_ENDPOINT);

    let sdk_config = cfg_loader.load().await;
    S3Client::new(&sdk_config)
}

// Core function to download bytes from S3
pub async fn download_s3_bytes(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
) -> anyhow::Result<Vec<u8>> {
    debug!(%bucket, %key,"Downloading S3 object");
    let output = s3_client
        .get_object()
        .bucket(bucket)
        .key(key)
        .send()
        .await
        .map_err(|e| {
            error!(error = %e, %bucket, %key,"Failed to download S3 object");
            e
        })?;

    let bytes = output
        .body
        .collect()
        .await
        .map(|data| data.into_bytes().to_vec())
        .map_err(|e| {
            error!(error = %e,%bucket, %key, "Failed to read response body");
            e
        })?;

    debug!(
        %bucket,
        %key,
        bytes_len = %bytes.len(),
        "Successfully downloaded file from s3"
    );
    Ok(bytes)
}

// Core function to upload bytes to S3
pub async fn upload_s3_bytes(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
    bytes: Vec<u8>,
) -> anyhow::Result<()> {
    debug!(len=%bytes.len(), %bucket, %key,"Uploading bytes to S3 object");
    s3_client
        .put_object()
        .bucket(bucket)
        .key(key)
        .body(ByteStream::from(bytes))
        .send()
        .await
        .map_err(|err| {
            error!(%err,%bucket, %key,"Failed to upload S3 object");
            anyhow!(err)
        })?;
    debug!( %bucket, %key,"Successfully uploaded s3 object");
    Ok(())
}

pub async fn download_file(url: &str, timeout: Duration) -> anyhow::Result<Vec<u8>> {
    info!(url, "Downloading file");
    let client = reqwest::Client::new();
    let response_result = client.get(url).timeout(timeout).send().await;

    let response = match response_result {
        Ok(res) => res,
        Err(err) => {
            tracing::error!(%err,"Encountered network error getting file.");
            return Err(anyhow::Error::from(err));
        }
    };

    if !response.status().is_success() {
        let status = response.status();
        let error_msg = format!("HTTP request failed with status code: {status}");
        error!(url, %status, "Download failed");
        bail!(error_msg);
    }

    let bytes = response.bytes().await?.to_vec();
    info!("Successfully downloaded {} bytes", bytes.len());
    Ok(bytes)
}

pub async fn fetch_case_filing_from_s3(
    s3_client: &S3Client,
    case_name: &str,
    jurisdiction: &JurisdictionInfo,
) -> anyhow::Result<GenericCase> {
    info!(case_name, jurisdiction_name=%jurisdiction.jurisdiction, "Fetching case filing from S3");
    let key = get_case_s3_key(case_name, jurisdiction);
    let bytes = download_s3_bytes(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key).await?;
    let case = serde_json::from_slice(&bytes)?;
    info!("Successfully deserialized case filing");
    Ok(case)
}

pub async fn fetch_attachment_data_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<RawAttachment> {
    info!(%hash, "Fetching attachment data from S3");
    let key = get_raw_attach_obj_key(hash);
    let bytes = download_s3_bytes(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key).await?;
    info!(%key, "Successfully got file from s3.");
    match serde_json::from_slice(&bytes) {
        Ok(attachment) => {
            info!("Successfully deserialized attachment data");
            Ok(attachment)
        }
        Err(err) => {
            let display_bytes = String::from_utf8_lossy(&bytes[0..100]);
            info!(%err,%key, json_snippet = %display_bytes, "Couldnt deserialze attachment from s3.");
            Err(anyhow::Error::from(err))
        }
    }
}

pub async fn fetch_attachment_file_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<Vec<u8>> {
    info!(%hash, "Fetching attachment file from S3");
    let key = get_raw_attach_file_key(hash);
    download_s3_bytes(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key).await
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

pub async fn push_case_to_s3_and_db(
    s3_client: &S3Client,
    case: &mut GenericCase,
    jurisdiction: &JurisdictionInfo,
) -> anyhow::Result<()> {
    info!(case_number = %case.case_number, "Pushing case to S3 and DB");
    let key = get_case_s3_key(&case.case_number, &jurisdiction);
    debug!("Pushing case with key: {}", key);
    case.indexed_at = offset::Utc::now();
    let case_jsonified = serde_json::to_string(case)?;
    upload_s3_bytes(
        s3_client,
        &OPENSCRAPERS_S3_OBJECT_BUCKET,
        &key,
        case_jsonified.into_bytes(),
    )
    .await?;
    info!("Successfully pushed case to S3");
    // TODO: Implement database update
    Ok(())
}

pub async fn list_cases_for_jurisdiction(
    s3_client: &S3Client,
    jurisdiction_name: &str,
    state: &str,
    country: &str,
) -> anyhow::Result<Vec<String>> {
    info!(
        jurisdiction_name,
        state, country, "Listing cases for jurisdiction"
    );
    let prefix = format!("objects/{country}/{state}/{jurisdiction_name}/");
    let mut case_names = Vec::new();
    info!("Listing cases with prefix: {}", prefix);

    let mut stream = s3_client
        .list_objects_v2()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .prefix(&prefix)
        .into_paginator()
        .send();

    while let Some(result) = stream.next().await {
        for object in result?.contents() {
            if let Some(key) = object.key() {
                info!(%key, "Found list attachment object");
                if key.ends_with(".json") {
                    if let Some(filename) = Path::new(key).file_name() {
                        if let Some(filestem) = filename.to_str().unwrap().strip_suffix(".json") {
                            case_names.push(filestem.to_string());
                        }
                    }
                }
            }
        }
    }

    info!("Found {} cases for jurisdiction", case_names.len());
    Ok(case_names)
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
    let dumped_data = serde_json::to_string(&raw_att)?;
    let obj_key = get_raw_attach_obj_key(raw_att.hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;

    upload_s3_bytes(s3_client, bucket, &obj_key, dumped_data.into_bytes()).await?;
    info!("Successfully pushed metadata object to S3");

    Ok(())
}
