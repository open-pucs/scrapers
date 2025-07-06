use crate::types::{AttachmentTextQuality, GenericCase, RawAttachment, RawAttachmentText};
use anyhow::{anyhow, Result};
use aws_sdk_s3::{primitives::ByteStream, Client as S3Client};
use blake2::{Blake2b, Digest};
use chrono::Utc;
use redis::AsyncCommands;
use reqwest;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::time::Duration;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tokio::time::sleep;

const OPENSCRAPERS_S3_OBJECT_BUCKET: &str = "openscrapers";
const CRIMSON_URL: &str = "http://localhost:8000"; // Replace with your actual Crimson URL

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

fn get_raw_attach_obj_key(hash: &str) -> String {
    format!("raw/metadata/{}.json", hash)
}

fn get_raw_attach_file_key(hash: &str) -> String {
    format!("raw/file/{}", hash)
}

fn generate_s3_object_uri_from_key(key: &str) -> String {
    format!(
        "https://{}.s3.amazonaws.com/{}",
        OPENSCRAPERS_S3_OBJECT_BUCKET,
        key
    )
}

pub async fn start_workers() -> Result<()> {
    let shared_config = aws_config::load_from_env().await;
    let s3_client = S3Client::new(&shared_config);
    let redis_client = redis::Client::open("redis://127.0.0.1/")?;
    let mut redis_con = redis_client.get_tokio_connection().await?;

    loop {
        let result: Result<String> = redis_con.brpop("case_queue", 0).await;
        if let Ok(json_data) = result {
            let case: GenericCase = serde_json::from_str(&json_data)?;
            let s3_client_clone = s3_client.clone();
            tokio::spawn(async move {
                if let Err(e) = process_case(case, s3_client_clone).await {
                    eprintln!("Error processing case: {:?}", e);
                }
            });
        }
    }
}

async fn process_case(case: GenericCase, s3_client: S3Client) -> Result<()> {
    if let Some(filings) = case.filings {
        for filing in filings {
            for mut attachment in filing.attachments {
                let file_path = download_file(&attachment.url).await?;
                let hash = blake2b_hash_from_file(&file_path).await?;
                let hash_str = base64::encode(&hash);
                attachment.hash = Some(hash_str.clone());

                let mut raw_attachment = RawAttachment {
                    hash: hash_str.clone(),
                    name: attachment.name.clone(),
                    extension: attachment.document_extension.clone().unwrap_or_default(),
                    text_objects: vec![],
                };

                if raw_attachment.extension == "pdf" {
                    let text = process_pdf_text_using_crimson(&raw_attachment.hash).await?;
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
    }
    Ok(())
}

async fn process_pdf_text_using_crimson(attachment_hash_from_s3: &str) -> Result<String> {
    let file_key = get_raw_attach_file_key(attachment_hash_from_s3);
    let s3_url = generate_s3_object_uri_from_key(&file_key);

    let crimson_params = CrimsonPDFIngestParamsS3 { s3_uri: s3_url };
    let client = reqwest::Client::new();
    let post_url = format!("{}/v1/ingest/s3", CRIMSON_URL);

    let initial_response = client
        .post(&post_url)
        .json(&crimson_params)
        .send()
        .await?;
    let initial_data: CrimsonInitialResponse = initial_response.json().await?;

    let check_url = format!("{}/v1/ingest/status/{}", CRIMSON_URL, initial_data.request_check_leaf);

    loop {
        sleep(Duration::from_secs(3)).await;
        let status_response = client.get(&check_url).send().await?;
        let status_data: CrimsonStatusResponse = status_response.json().await?;

        if status_data.completed {
            if status_data.success {
                return Ok(status_data.markdown.unwrap_or_default());
            } else {
                return Err(anyhow!(
                    "Crimson processing failed: {}",
                    status_data.error.unwrap_or_default()
                ));
            }
        }
    }
}

async fn push_raw_attach_to_s3(
    s3_client: &S3Client,
    raw_att: RawAttachment,
    file_path: &str,
) -> Result<()> {
    let dumped_data = serde_json::to_string(&raw_att)?;
    let obj_key = get_raw_attach_obj_key(&raw_att.hash);
    let file_key = get_raw_attach_file_key(&raw_att.hash);

    s3_client
        .put_object()
        .bucket(OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(obj_key)
        .body(ByteStream::from(dumped_data.into_bytes()))
        .send()
        .await?;

    let body = ByteStream::from_path(Path::new(file_path)).await?;
    s3_client
        .put_object()
        .bucket(OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(file_key)
        .body(body)
        .send()
        .await?;

    Ok(())
}

async fn download_file(url: &str) -> Result<String> {
    let response = reqwest::get(url).await?;
    let temp_file_path = "temp_file";
    let mut dest = File::create(temp_file_path).await?;
    let content = response.bytes().await?;
    tokio::io::copy(&mut content.as_ref(), &mut dest).await?;
    Ok(temp_file_path.to_string())
}

async fn blake2b_hash_from_file(file_path: &str) -> Result<Vec<u8>> {
    let mut file = File::open(file_path).await?;
    let mut hasher = Blake2b::new();
    let mut buffer = [0; 1024];

    loop {
        let n = file.read(&mut buffer).await?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }

    Ok(hasher.finalize().to_vec())
}
