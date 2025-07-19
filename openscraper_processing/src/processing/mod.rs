use crate::s3_stuff::{
    download_file, generate_s3_object_uri_from_key, get_raw_attach_file_key,
    push_case_to_s3_and_db, push_raw_attach_file_to_s3, push_raw_attach_object_to_s3,
};
use crate::types::env_vars::CRIMSON_URL;
use crate::types::file_extension::FileExtension;
use crate::types::hash::Blake2bHash;
use crate::types::{
    AttachmentTextQuality, CaseWithJurisdiction, GenericAttachment, RawAttachment,
    RawAttachmentText,
};
use anyhow::{anyhow, bail};
use aws_sdk_s3::Client as S3Client;
use chrono::Utc;
use futures_util::future::join_all;
use serde::{Deserialize, Serialize};
use std::str::FromStr;
use std::time::Duration;
use tokio::sync::Semaphore;
use tokio::time::sleep;
use tracing::info;

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

const ATTACHMENT_DOWNLOAD_TRIES: usize = 2;
const DOWNLOAD_RETRY_DELAY_SECONDS: u64 = 2;

pub async fn process_case(
    jurisdiction_case: &CaseWithJurisdiction,
    s3_client: &S3Client,
) -> anyhow::Result<()> {
    let case = &jurisdiction_case.case;
    let sem = Semaphore::new(10); // Allow up to 10 concurrent tasks
    let mut return_case = case.to_owned();
    let mut attachment_tasks = Vec::with_capacity(case.filings.len());
    for filing in return_case.filings.iter_mut() {
        for attachment in filing.attachments.iter_mut() {
            let tmp_closure =
                async |attach: &mut GenericAttachment| -> anyhow::Result<RawAttachment> {
                    // Acquire permit from semaphore (waits if none available)
                    let permit = sem
                        .acquire()
                        .await
                        .expect("This should never panic since the semaphore never closes.");
                    let result = tokio::time::timeout(
                        Duration::from_secs(120),
                        process_attachment(s3_client, attach),
                    )
                    .await;
                    drop(permit);
                    match result {
                        Ok(Ok(raw_attach)) => {
                            attach.hash = Some(raw_attach.hash);
                            attach.document_extension = Some(raw_attach.extension.to_string());
                            Ok(raw_attach)
                        }
                        Ok(Err(err)) => {
                            tracing::error!(%err,"Failed to process attachment");
                            Err(err)
                        }
                        Err(err) => {
                            tracing::error!(%err, "Attachment processing timed out");
                            Err(anyhow::Error::from(err))
                        }
                    }
                };
            attachment_tasks.push(tmp_closure(attachment));
        }
    }
    tracing::info!(case_num=%case.case_number,"Created all attachment processing futures.");
    join_all(attachment_tasks).await;

    let jurisdiction = "ny_puc";
    let default_state = "ny";
    let default_country = "usa";
    tracing::info!(
        case_num=%case.case_number,
        state=%default_state,
        jurisdiction=%jurisdiction,
        "Finished all attachments, pushing case to db."
    );
    let s3_result = push_case_to_s3_and_db(
        s3_client,
        &mut return_case,
        jurisdiction,
        default_state,
        default_country,
    )
    .await;
    if let Err(err) = s3_result {
        tracing::error!(
            case_num=%case.case_number, 
            %err, 
            state=%default_state,
            jurisdiction=%jurisdiction,
            "Failed to push case to S3/DB");
        return Err(err);
    }

    tracing::info!(
        case_num=%case.case_number,
        state=%default_state,
        jurisdiction=%jurisdiction,
        "Successfully pushed case to db."
    );
    Ok(())
}

async fn process_attachment(
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
        download_file_content_validated_with_retries(&attachment.url, &extension).await?;
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

async fn download_file_content_validated_with_retries(
    url: &str,
    extension: &FileExtension,
) -> anyhow::Result<Vec<u8>> {
    let mut last_error: Option<anyhow::Error> = None;
    for _ in 0..ATTACHMENT_DOWNLOAD_TRIES {
        match download_file(url, Duration::from_secs(20)).await {
            Ok(file_contents) => {
                if let Err(err) = extension.is_valid_file_contents(&file_contents) {
                    tracing::error!(%extension,%url, %err,"Downloaded file did not match extension");
                    last_error = Some(anyhow::Error::from(err))
                } else {
                    return Ok(file_contents);
                }
            }
            Err(err) => {
                tracing::error!(%url, %err,"Encountered error downloading file");
                last_error = Some(err);
            }
        };
        sleep(Duration::from_secs(DOWNLOAD_RETRY_DELAY_SECONDS)).await;
    }

    tracing::error!(%extension,%url,"Could not download file from url dispite a bunch of retries.");

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

#[cfg(test)]
mod test;
