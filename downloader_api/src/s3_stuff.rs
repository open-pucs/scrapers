use anyhow::anyhow;
use futures_util::join;
use mycorrhiza_common::s3_generic::fetchers_and_getters::{S3Addr, S3DirectoryAddr};
use mycorrhiza_common::s3_generic::s3_uri::S3LocationWithCredentials;
use non_empty_string::non_empty_string;
use tracing::{debug, info};

use crate::types::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};
use crate::types::jurisdictions::JurisdictionInfo;
use crate::types::processed::ProcessedGenericDocket;
use crate::types::raw::{RawAttachment, RawGenericDocket};
use aws_sdk_s3::Client as S3Client;
use mycorrhiza_common::hash::Blake2bHash;

pub fn get_raw_attach_file_key(hash: Blake2bHash) -> String {
    let key = format!("raw/file/{hash}");
    debug!(%hash, "Generated raw attachment file key: {}", key);
    key
}

impl CannonicalS3ObjectLocation for RawAttachment {
    type AddressInfo = Blake2bHash;
    fn generate_object_key(hash: &Self::AddressInfo) -> String {
        format!("raw/metadata/{hash}.json")
    }
}

pub struct DocketAddress {
    pub docket_govid: String,
    pub jurisdiction: JurisdictionInfo,
}

impl CannonicalS3ObjectLocation for RawGenericDocket {
    type AddressInfo = DocketAddress;

    fn generate_object_key(addr: &Self::AddressInfo) -> String {
        let country = &*addr.jurisdiction.country;
        let state = &*addr.jurisdiction.state;
        let jurisdiction = &*addr.jurisdiction.jurisdiction;
        let case_name = &*addr.docket_govid;
        format!("objects_raw/{country}/{state}/{jurisdiction}/{case_name}")
    }
}
impl CannonicalS3ObjectLocation for ProcessedGenericDocket {
    type AddressInfo = DocketAddress;

    fn generate_object_key(addr: &Self::AddressInfo) -> String {
        let country = &*addr.jurisdiction.country;
        let state = &*addr.jurisdiction.state;
        let jurisdiction = &*addr.jurisdiction.jurisdiction;
        let case_name = &*addr.docket_govid;
        format!("objects/{country}/{state}/{jurisdiction}/{case_name}")
    }
}

pub trait CannonicalS3ObjectLocation: serde::Serialize + serde::de::DeserializeOwned {
    type AddressInfo;
    fn generate_object_key(addr: &Self::AddressInfo) -> String;
}

pub fn get_openscrapers_json_key<T: CannonicalS3ObjectLocation>(addr: &T::AddressInfo) -> String {
    T::generate_object_key(addr) + ".json"
}

pub fn get_s3_json_uri<T: CannonicalS3ObjectLocation>(addr: &T::AddressInfo) -> String {
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let key = get_openscrapers_json_key::<T>(addr);
    let credentials = &*OPENSCRAPERS_S3;
    S3LocationWithCredentials::from_key_bucket_and_credentials(&key, bucket, credentials)
        .to_string()
}

pub async fn download_openscrapers_object<T: CannonicalS3ObjectLocation>(
    s3_client: &S3Client,
    addr: &T::AddressInfo,
) -> anyhow::Result<T> {
    let key = get_openscrapers_json_key::<T>(addr);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    S3Addr::new(s3_client, bucket, &key).download_json().await
}

pub async fn upload_object<T: CannonicalS3ObjectLocation>(
    s3_client: &S3Client,
    addr: &T::AddressInfo,
    object: &T,
) -> anyhow::Result<()> {
    let key = get_openscrapers_json_key::<T>(addr);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    S3Addr::new(s3_client, bucket, &key)
        .upload_json(&object)
        .await
}

pub async fn delete_openscrapers_s3_object<T: CannonicalS3ObjectLocation>(
    s3_client: &S3Client,
    addr: &T::AddressInfo,
) -> anyhow::Result<()> {
    let key = get_openscrapers_json_key::<T>(addr);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    S3Addr::new(s3_client, bucket, &key).delete_file().await
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
    info!("Creating S3 client");
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

pub async fn fetch_attachment_file_from_s3_with_filename(
    s3_client: &S3Client,
    hash: Blake2bHash,
) -> anyhow::Result<(String, Vec<u8>)> {
    info!(%hash, "Fetching attachment file from S3");
    let key = get_raw_attach_file_key(hash);
    let location = S3Addr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &key);
    let bytes_future = location.download_bytes();
    let metadata_future = download_openscrapers_object::<RawAttachment>(s3_client, &hash);
    let (Ok(bytes), metadata) = join!(bytes_future, metadata_future) else {
        return Err(anyhow!("fetching bytes failed."));
    };

    let filename = metadata
        .ok()
        .map(|v| v.name + "." + &v.extension.to_string())
        .unwrap_or_else(|| non_empty_string!("unknown_filename.pdf"));
    Ok((filename.to_string(), bytes))
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
    let obj_key = get_openscrapers_json_key::<RawAttachment>(&hash);
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
    info!("Successfully pushed file to S3");

    Ok(())
}
