use crate::processing::attachments::OpenscrapersExtraData;
use crate::s3_stuff::push_case_to_s3_and_db;
use crate::types::data_processing_traits::{DownloadIncomplete, Revalidate};
use crate::types::openscraper_types::{
    CaseWithJurisdiction, GenericAttachment, GenericCase, JurisdictionInfo, RawAttachment
};
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

impl DownloadIncomplete for GenericCase {
    type ExtraData = OpenscrapersExtraData;
    type SucessData = ();
    async fn download_incomplete(
            &mut self,
            extra: &Self::ExtraData,
        ) -> anyhow::Result<Self::SucessData> {

        let attachment_refs = make_reflist_of_attachments(self);
        let tmp_closure =
            async |attach: &mut GenericAttachment| -> anyhow::Result<RawAttachment> {
                // Acquire permit from semaphore (waits if none available)
                let result = tokio::time::timeout(
                    Duration::from_secs(120),
                attach.download_incomplete(extra)
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
        const CONCURRENT_ATTACHMENTS :usize = 2;
        let _ = futures_stream.buffer_unordered(CONCURRENT_ATTACHMENTS).count().await;
        return Ok(());
    }
}


pub async fn process_case(
    mut case: GenericCase,
    extra_data: &OpenscrapersExtraData,
    download_files: bool,
) -> anyhow::Result<()> {
    let (s3_client,jur_info) = extra_data;
    case.revalidate();
    // TODO: Fetch data from s3 and merge the cache results.
    if download_files {
        case.download_incomplete(extra_data).await;
    }

    tracing::info!(
        case_num=%case.case_govid,
        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Finished all attachments, pushing case to db."
    );
    let s3_result = push_case_to_s3_and_db(
        s3_client,
        &mut case,
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
