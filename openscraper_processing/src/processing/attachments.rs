use crate::processing::{CrimsonInitialResponse, CrimsonPDFIngestParamsS3, CrimsonStatusResponse};
use crate::s3_stuff::{
    generate_s3_object_uri_from_key, get_raw_attach_file_key, push_raw_attach_file_to_s3,
    push_raw_attach_object_to_s3,
};
use crate::types::env_vars::CRIMSON_URL;
use crate::types::file_extension::FileExtension;
use crate::types::hash::Blake2bHash;
use crate::types::{AttachmentTextQuality, GenericAttachment, RawAttachment, RawAttachmentText};
use anyhow::{anyhow, bail};
use aws_sdk_s3::Client as S3Client;
use chrono::Utc;
use std::str::FromStr;
use std::time::Duration;
use tokio::time::sleep;
use tracing::info;

use super::file_fetching::InternetFileFetch;

const ATTACHMENT_DOWNLOAD_TRIES: usize = 2;
const DOWNLOAD_RETRY_DELAY_SECONDS: u64 = 2;
pub async fn process_attachment_in_regular_pipeline(
    s3_client: &S3Client,
    attachment: &GenericAttachment,
) -> anyhow::Result<RawAttachment> {
    if attachment.document_extension.is_none() {
        bail!("Extension does not exist!")
    };
    let invalid_ext = attachment.document_extension.as_ref().unwrap();
    let extension = match FileExtension::from_str(invalid_ext) {
        Ok(val) => val,
        Err(err) => bail!(err),
    };

    info!(url=%attachment.url,"Trying to download attachment file.");

    let file_contents =
        download_file_content_validated_with_retries(&*attachment.url, &extension).await?;
    let hash = Blake2bHash::from_bytes(&file_contents);
    info!(%hash, url=%attachment.url,"Successfully downloaded file.");

    let mut raw_attachment = RawAttachment {
        hash,
        name: attachment.name.clone(),
        extension: extension.clone(),
        text_objects: vec![],
    };

    push_raw_attach_file_to_s3(s3_client, &raw_attachment, file_contents).await?;
    info!(%hash,"Pushed raw file to s3.");

    if raw_attachment.extension == FileExtension::Pdf {
        info!(%hash,"Sending request to crimson to process pdf.");
        let text_result = process_pdf_text_using_crimson(raw_attachment.hash).await;
        match text_result {
            Ok(text) => {
                info!(%hash,"Completed text processing.");
                let text_obj = RawAttachmentText {
                    quality: AttachmentTextQuality::Low,
                    language: "en".to_string(),
                    text,
                    timestamp: Utc::now(),
                };
                raw_attachment.text_objects.push(text_obj);
            }
            Err(err) => {
                tracing::error!(%err,%hash,"Encountered error processing text for pdf.")
            }
        }
    }
    push_raw_attach_object_to_s3(s3_client, &raw_attachment).await?;
    Ok(raw_attachment)
}

async fn download_file_content_validated_with_retries<T: InternetFileFetch>(
    to_fetch: T,
    extension: &FileExtension,
) -> anyhow::Result<Vec<u8>> {
    let mut last_error: Option<anyhow::Error> = None;
    for _ in 0..ATTACHMENT_DOWNLOAD_TRIES {
        match to_fetch
            .download_file_with_timeout(Duration::from_secs(20))
            .await
        {
            Ok(file_contents) => {
                if let Err(err) = extension.is_valid_file_contents(&file_contents) {
                    tracing::error!(%extension,?to_fetch, %err,"Downloaded file did not match extension");
                    last_error = Some(anyhow::Error::from(err))
                } else {
                    return Ok(file_contents);
                }
            }
            Err(err) => {
                tracing::error!(?to_fetch, %err,"Encountered error downloading file");
                last_error = Some(err);
            }
        };
        sleep(Duration::from_secs(DOWNLOAD_RETRY_DELAY_SECONDS)).await;
    }

    tracing::error!(%extension,?to_fetch,"Could not download file from url dispite a bunch of retries.");

    Err(last_error.unwrap_or(anyhow!(
        "UNREACHABLE CODE: Should have not gotten to last step without error being set"
    )))
}

async fn process_pdf_text_using_crimson(
    attachment_hash_from_s3: Blake2bHash,
) -> anyhow::Result<String> {
    let file_key = get_raw_attach_file_key(attachment_hash_from_s3);
    let s3_url = generate_s3_object_uri_from_key(&file_key);

    let crimson_params = CrimsonPDFIngestParamsS3 { s3_uri: s3_url };
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()?;
    let crimson_url = &**CRIMSON_URL;
    let post_url = format!("{crimson_url}/v1/ingest/s3");

    let initial_response = client.post(&post_url).json(&crimson_params).send().await?;
    let initial_data: CrimsonInitialResponse = initial_response.json().await?;

    let check_url = format!(
        "{}/{}",
        crimson_url.trim_end_matches('/'),
        initial_data.request_check_leaf.trim_start_matches('/')
    );

    for _ in 1..1000 {
        sleep(Duration::from_secs(3)).await;
        let status_response = match client.get(&check_url).send().await {
            Ok(val) => val,
            Err(err) => {
                tracing::error!(%err,%check_url,"got bad response from crimson");
                return Err(err.into());
            }
        };
        let response_text = match status_response.text().await {
            Ok(text) => text,
            Err(err) => {
                tracing::error!(%err,%check_url, "Failed to get text from Crimson response");
                return Err(err.into());
            }
        };

        let status_data: CrimsonStatusResponse = match serde_json::from_str(&response_text) {
            Ok(data) => data,
            Err(err) => {
                tracing::error!(%err, response_text, "Crimson did not return valid JSON");
                return Err(err.into());
            }
        };

        if status_data.completed {
            if status_data.success {
                let markdown = status_data.markdown.unwrap_or_default();
                return Ok(markdown.to_string());
            } else {
                let error = status_data.error.unwrap_or_default();
                tracing::error!(crimson_error_string = error,%check_url,"Crimson processing failed");
                bail!("Crimson processing failed: {}", error);
            }
        }
    }
    bail!("Crimson processing failed after 1000 attempts.")
}
