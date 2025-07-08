use std::env;
use std::path::{Path, PathBuf};
use std::time::{Instant, SystemTime};

use anyhow::bail;
use aws_config::{BehaviorVersion, Region};
use aws_sdk_s3::config::Credentials;
use chrono::{DateTime, offset};
use tokio::fs::File;

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
    format!("raw/metadata/{hash}.json")
}

pub fn get_raw_attach_file_key(hash: Blake2bHash) -> String {
    format!("raw/file/{hash}")
}

pub fn generate_s3_object_uri_from_key(key: &str) -> String {
    S3Location::default_from_key(key).to_string()
}
pub async fn make_s3_client() -> S3Client {
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

pub async fn push_raw_attach_to_s3(
    s3_client: &S3Client,
    raw_att: RawAttachment,
    file_path: &str,
) -> anyhow::Result<()> {
    let dumped_data = serde_json::to_string(&raw_att)?;
    let obj_key = get_raw_attach_obj_key(raw_att.hash);
    let file_key = get_raw_attach_file_key(raw_att.hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;

    s3_client
        .put_object()
        .bucket(bucket)
        .key(obj_key)
        .body(ByteStream::from(dumped_data.into_bytes()))
        .send()
        .await?;

    let body = ByteStream::from_path(Path::new(file_path)).await?;
    s3_client
        .put_object()
        .bucket(bucket)
        .key(file_key)
        .body(body)
        .send()
        .await?;

    Ok(())
}

pub async fn download_file(url: &str) -> anyhow::Result<String> {
    let response = reqwest::get(url).await?;
    let random_name = "blaahblah";
    let temp_file_path = format!("tmp/downloads/{random_name}");
    let mut dest = File::create(&temp_file_path).await?;
    let content = response.bytes().await?;
    tokio::io::copy(&mut content.as_ref(), &mut dest).await?;
    Ok(temp_file_path)
}

pub fn get_case_s3_key(
    case_name: &str,
    jurisdiction_name: &str,
    state: &str,
    country: &str,
) -> String {
    format!("objects/{country}/{state}/{jurisdiction_name}/{case_name}.json")
}

pub async fn fetch_case_filing_from_s3(
    s3_client: &S3Client,
    case_name: &str,
    jurisdiction_name: &str,
    state: &str,
    country: &str,
) -> anyhow::Result<GenericCase> {
    let key = get_case_s3_key(case_name, jurisdiction_name, state, country);
    let output = s3_client
        .get_object()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(key)
        .send()
        .await?;
    let bytes = output.body.collect().await?.into_bytes();
    let case: GenericCase = serde_json::from_slice(&bytes)?;
    Ok(case)
}

pub async fn fetch_attachment_data_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<RawAttachment> {
    let obj_key = get_raw_attach_obj_key(hash);
    let result = s3_client
        .get_object()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(obj_key)
        .send()
        .await?;
    let bytes = result.body.collect().await?.into_bytes();
    let raw_attach: RawAttachment = serde_json::from_slice(&bytes)?;
    Ok(raw_attach)
}

pub async fn fetch_attachment_file_from_s3(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<PathBuf> {
    let obj_key = get_raw_attach_file_key(hash);
    let mut temp_path = env::temp_dir();
    temp_path.push(hash.to_string());

    let mut file = File::create(&temp_path).await?;
    let mut stream = s3_client
        .get_object()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(obj_key)
        .send()
        .await?
        .body;

    while let Some(chunk) = stream.try_next().await? {
        tokio::io::copy(&mut chunk.as_ref(), &mut file).await?;
    }

    Ok(temp_path)
}

pub async fn does_openscrapers_attachment_exist(s3_client: &S3Client, hash: Blake2bHash) -> bool {
    let obj_key = get_raw_attach_obj_key(hash);
    let file_key = get_raw_attach_file_key(hash);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;

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

    obj_exists.is_ok() && file_exists.is_ok()
}

pub async fn push_case_to_s3_and_db(
    s3_client: &S3Client,
    case: &mut GenericCase,
    jurisdiction_name: &str,
    state: &str,
    country: &str,
) -> anyhow::Result<()> {
    let key = get_case_s3_key(&case.case_number, jurisdiction_name, state, country);
    case.indexed_at = offset::Utc::now();
    let case_jsonified = serde_json::to_string(case)?;
    s3_client
        .put_object()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(key)
        .body(ByteStream::from(case_jsonified.into_bytes()))
        .send()
        .await?;
    // TODO: Implement database update
    Ok(())
}

pub async fn list_cases_for_jurisdiction(
    s3_client: &S3Client,
    jurisdiction_name: &str,
    state: &str,
    country: &str,
) -> anyhow::Result<Vec<String>> {
    let prefix = format!("objects/{country}/{state}/{jurisdiction_name}/");
    let mut case_names = Vec::new();

    let mut stream = s3_client
        .list_objects_v2()
        .bucket(&**OPENSCRAPERS_S3_OBJECT_BUCKET)
        .prefix(prefix)
        .into_paginator()
        .send();

    while let Some(result) = stream.next().await {
        for object in result?.contents() {
            if let Some(key) = object.key() {
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

    Ok(case_names)
}
