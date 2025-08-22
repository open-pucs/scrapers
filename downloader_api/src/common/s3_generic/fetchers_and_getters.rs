use anyhow::anyhow;
use aws_sdk_s3::{Client as S3Client, primitives::ByteStream};
use futures_util::join;
use non_empty_string::non_empty_string;
use rkyv::api::high::{HighSerializer, HighValidator};
use rkyv::bytecheck::CheckBytes;
use rkyv::de::Pool;
use rkyv::rancor::Strategy;
use rkyv::ser::allocator::{Arena, ArenaHandle};
use rkyv::ser::sharing::Share;
use rkyv::util::AlignedVec;
use rkyv::{Archive, Serialize};
use std::convert::Infallible;
use std::ops::Deref;
use std::path::Path;
use thiserror::Error;
use tracing::{debug, error, info};

// Core function to download bytes from S3
pub async fn download_s3_json<T: serde::de::DeserializeOwned>(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
) -> anyhow::Result<T> {
    let bytes = download_s3_bytes(s3_client, bucket, key).await?;
    let case = serde_json::from_slice(&bytes)?;
    Ok(case)
}

pub async fn upload_s3_json<T: serde::Serialize>(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
    obj: &T,
) -> anyhow::Result<()> {
    let obj_json_bytes = serde_json::to_vec(obj)?;
    upload_s3_bytes(s3_client, bucket, key, obj_json_bytes).await
}

pub async fn upload_s3_rkyv<T>(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
    obj: &T,
) -> anyhow::Result<()>
where
    T: Archive
        + for<'a> Serialize<HighSerializer<AlignedVec, ArenaHandle<'a>, rkyv::rancor::Error>>,
{
    let bytes = rkyv::to_bytes(obj)?;
    upload_s3_bytes(s3_client, bucket, key, bytes.to_vec()).await
}

pub async fn download_s3_rkyv_deserialize<T>(
    s3_client: &S3Client,
    bucket: &str,
    key: &str,
) -> anyhow::Result<T>
where
    T: Archive,
    T::Archived: for<'a> CheckBytes<HighValidator<'a, rkyv::rancor::Error>>
        + rkyv::Deserialize<T, Strategy<Pool, rkyv::rancor::Error>>,
{
    let bytes = download_s3_bytes(s3_client, bucket, key).await?;
    let value = rkyv::from_bytes(&bytes)?;
    Ok(value)
}
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

pub async fn delete_s3_file(s3_client: &S3Client, bucket: &str, key: &str) -> anyhow::Result<()> {
    debug!( %bucket, %key,"Deleting file from S3");
    s3_client
        .delete_object()
        .bucket(bucket)
        .key(key)
        .send()
        .await
        .map_err(|err| {
            error!(%err,%bucket, %key,"Failed to delete s3 file");
            anyhow!(err)
        })?;
    debug!( %bucket, %key,"Successfully uploaded s3 object");
    Ok(())
}

pub async fn delete_all_with_prefix(
    s3_client: &S3Client,
    bucket: &str,
    prefix: &str,
) -> anyhow::Result<()> {
    let mut continuation_token: Option<String> = None;

    loop {
        let mut list_request = s3_client.list_objects_v2().bucket(bucket).prefix(prefix);
        if let Some(token) = continuation_token {
            list_request = list_request.continuation_token(token);
        }
        let response = list_request.send().await?;
        if let Some(objects) = response.contents {
            for object in objects {
                if let Some(key) = object.key {
                    delete_s3_file(s3_client, bucket, &key).await?;
                }
            }
        }
        match response.is_truncated {
            Some(true) => continuation_token = response.next_continuation_token,
            _ => break,
        }
    }
    Ok(())
}

pub async fn match_all_with_prefix(
    s3_client: &S3Client,
    bucket: &str,
    prefix: &str,
) -> anyhow::Result<Vec<String>> {
    let mut prefix_names = Vec::new();

    let mut stream = s3_client
        .list_objects_v2()
        .bucket(bucket)
        .prefix(prefix)
        .into_paginator()
        .send();

    while let Some(result) = stream.next().await {
        for object in result?.contents() {
            if let Some(key) = object.key() {
                info!(%key, "Found list attachment object");
                if key.ends_with(".json")
                    && let Some(filename) = Path::new(key).file_name()
                    && let Some(filestem) = filename.to_str()
                {
                    prefix_names.push(filestem.to_string());
                }
            }
        }
    }
    Ok(prefix_names)
}

