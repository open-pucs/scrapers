use crate::s3_stuff::push_case_to_s3_and_db;
use crate::types::{
    CaseWithJurisdiction, GenericAttachment, GenericCase, RawAttachment
};
use attachments::process_attachment_in_regular_pipeline;
use aws_sdk_s3::Client as S3Client;
use futures_util::{stream, StreamExt};
use serde::{Deserialize, Serialize};
use std::time::Duration;

pub mod attachments;
pub mod file_fetching;

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


pub fn make_reflist_of_attachments(case: &mut GenericCase) -> Vec<&mut GenericAttachment> {
    let mut case_refs= Vec::with_capacity(case.filings.len());
    for filling in case.filings.iter_mut() {
        for attachment in filling.attachments.iter_mut() {
            case_refs.push(attachment);
        }
    }
    case_refs
}

pub async fn process_case(
    jurisdiction_case: &CaseWithJurisdiction,
    s3_client: &S3Client,
) -> anyhow::Result<()> {
    let case = &jurisdiction_case.case;
    let jurisdiction_info = &jurisdiction_case.jurisdiction;
    let mut return_case = case.to_owned();
    // let mut attachment_tasks = Vec::with_capacity(case.filings.len());
    let attachment_refs = make_reflist_of_attachments(&mut return_case);
    let tmp_closure =
        async |attach: &mut GenericAttachment| -> anyhow::Result<RawAttachment> {
            // Acquire permit from semaphore (waits if none available)
            let result = tokio::time::timeout(
                Duration::from_secs(120),
                process_attachment_in_regular_pipeline(s3_client,jurisdiction_info, attach),
            )
            .await;
            match result {
                Ok(Ok(raw_attach)) => {
                    attach.hash = Some(raw_attach.hash);
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
    let futures_stream = stream::iter(attachment_refs.into_iter().map(tmp_closure));
    const CONCURRENT_ATTACHMENTS :usize = 3;
    let _ = futures_stream.buffer_unordered(CONCURRENT_ATTACHMENTS).count().await;
    // Asychronously process all of these using the futures library
    tracing::info!(case_num=%case.case_govid,"Created all attachment processing futures.");

    let jur_info =&jurisdiction_case.jurisdiction;
    tracing::info!(
        case_num=%case.case_govid,
        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Finished all attachments, pushing case to db."
    );
    let s3_result = push_case_to_s3_and_db(
        s3_client,
        &mut return_case,
        jur_info
    )
    .await;
    if let Err(err) = s3_result {
        tracing::error!(
            case_num=%case.case_govid, 
            %err, 
            state=%jur_info.state,
            jurisdiction=%jur_info.jurisdiction,
            "Failed to push case to S3/DB");
        return Err(err);
    }

    tracing::info!(
        case_num=%case.case_govid,

        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Successfully pushed case to db."
    );
    Ok(())
}


#[cfg(test)]
mod test;
