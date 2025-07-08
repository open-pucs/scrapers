use crate::s3_stuff::{
    download_file, generate_s3_object_uri_from_key, get_raw_attach_file_key, make_s3_client,
    push_raw_attach_to_s3,
};
use crate::types::env_vars::{
    CRIMSON_URL, OPENSCRAPERS_REDIS_DOMAIN, OPENSCRAPERS_S3_OBJECT_BUCKET,
};
use crate::types::hash::Blake2bHash;
use crate::types::{AttachmentTextQuality, GenericCase, RawAttachment, RawAttachmentText};
use anyhow::{anyhow, bail};
use aws_sdk_s3::{Client as S3Client, primitives::ByteStream};
use blake2::{Blake2b, Digest};
use chrono::Utc;
use redis::{AsyncCommands, RedisError};
use reqwest;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::time::Duration;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tokio::time::sleep;
use tracing::warn;

#[derive(Serialize)]
struct CrimsonPDFIngestParamsS3 {
    s3_uri: String,
}

#[derive(Deserialize, Debug)]
struct CrimsonInitialResponse {
    request_check_leaf: String,
}

#[derive(Deserialize, Debug)]
struct CrimsonStatusResponse {
    completed: bool,
    success: bool,
    markdown: Option<String>,
    error: Option<String>,
}

// use futures::prelude::*;
// use redis::AsyncCommands;
//
// let client = redis::Client::open("redis://127.0.0.1/").unwrap();
// let mut con = client.get_multiplexed_async_connection().await?;
//
// let _: () = con.set("key1", b"foo").await?;
//
// redis::cmd("SET").arg(&["key2", "bar"]).exec_async(&mut con).await?;
//
// let result = redis::cmd("MGET")
//  .arg(&["key1", "key2"])
//  .query_async(&mut con)
//  .await;
// assert_eq!(result, Ok(("foo".to_string(), b"bar".to_vec())));
pub async fn start_workers() -> anyhow::Result<()> {
    let s3_client = make_s3_client().await;
    let redis_client = redis::Client::open(&**OPENSCRAPERS_REDIS_DOMAIN)?;
    let mut redis_con = redis_client.get_multiplexed_async_connection().await?;

    loop {
        let result: Result<String, RedisError> = redis_con.brpop("generic_cases", 0.0).await;
        if let Ok(json_data) = result {
            let case: GenericCase = serde_json::from_str(&json_data)?;
            let s3_client_clone = s3_client.clone();
            tokio::spawn(async move {
                if let Err(e) = process_case(case, s3_client_clone).await {
                    warn!(error = e.to_string(), "Error processing case");
                }
            });
        } else {
            sleep(Duration::from_secs(2)).await;
        }
    }
}

async fn process_case(case: GenericCase, s3_client: S3Client) -> anyhow::Result<()> {
    let filings = case.filings;
    for filing in filings {
        for mut attachment in filing.attachments {
            let file_path = download_file(&attachment.url).await?;
            let hash = Blake2bHash::from_file(&file_path)?;
            attachment.hash = Some(hash);

            let mut raw_attachment = RawAttachment {
                hash,
                name: attachment.name.clone(),
                extension: attachment.document_extension.clone().unwrap_or_default(),
                text_objects: vec![],
            };

            if raw_attachment.extension == "pdf" {
                let text = process_pdf_text_using_crimson(raw_attachment.hash).await?;
                let text_obj = RawAttachmentText {
                    quality: AttachmentTextQuality::Low,
                    language: "en".to_string(),
                    text,
                    timestamp: Utc::now(),
                };
                raw_attachment.text_objects.push(text_obj);
            }

            push_raw_attach_to_s3(&s3_client, raw_attachment, &file_path).await?;
        }
    }
    Ok(())
}

async fn process_pdf_text_using_crimson(
    attachment_hash_from_s3: Blake2bHash,
) -> anyhow::Result<String> {
    let file_key = get_raw_attach_file_key(attachment_hash_from_s3);
    let s3_url = generate_s3_object_uri_from_key(&file_key);

    let crimson_params = CrimsonPDFIngestParamsS3 { s3_uri: s3_url };
    let client = reqwest::Client::new();
    let crimson_url = &**CRIMSON_URL;
    let post_url = format!("{crimson_url}/v1/ingest/s3");

    let initial_response = client.post(&post_url).json(&crimson_params).send().await?;
    let initial_data: CrimsonInitialResponse = initial_response.json().await?;

    let check_url = format!(
        "{}/v1/ingest/status/{}",
        crimson_url, initial_data.request_check_leaf
    );

    for _ in 1..1000 {
        sleep(Duration::from_secs(3)).await;
        let status_response = client.get(&check_url).send().await?;
        let status_data: CrimsonStatusResponse = status_response.json().await?;

        if status_data.completed {
            if status_data.success {
                return Ok(status_data.markdown.unwrap_or_default());
            } else {
                bail!(
                    "Crimson processing failed: {}",
                    status_data.error.unwrap_or_default()
                );
            }
        }
    }
    bail!("Crimson processing failed after 1000 attempts.")
}
