use crate::s3_stuff::push_case_to_s3_and_db;
use crate::types::{
    CaseWithJurisdiction, GenericAttachment, RawAttachment,
};
use attachments::process_attachment_in_regular_pipeline;
use aws_sdk_s3::Client as S3Client;
use futures_util::future::join_all;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tokio::sync::Semaphore;

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


pub async fn process_case(
    jurisdiction_case: &CaseWithJurisdiction,
    s3_client: &S3Client,
) -> anyhow::Result<()> {
    let case = &jurisdiction_case.case;
    let jurisdiction_info = &jurisdiction_case.jurisdiction;
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
                        process_attachment_in_regular_pipeline(s3_client,jurisdiction_info, attach),
                    )
                    .await;
                    drop(permit);
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
            attachment_tasks.push(tmp_closure(attachment));
        }
    }
    tracing::info!(case_num=%case.case_govid,"Created all attachment processing futures.");
    join_all(attachment_tasks).await;

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
