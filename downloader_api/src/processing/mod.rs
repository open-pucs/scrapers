use crate::processing::attachments::OpenscrapersExtraData;
use crate::s3_stuff::{DocketAddress, download_openscrapers_object, upload_object};
use crate::types::data_processing_traits::{DownloadIncomplete, ProcessFrom};
use crate::types::processed::{ProcessedGenericAttachment, ProcessedGenericDocket};
use crate::types::raw::RawGenericDocket;
use futures_util::{StreamExt, stream};
use serde::{Deserialize, Serialize};

pub mod attachments;
pub mod file_fetching;
pub mod llm_prompts;
pub mod match_raw_processed;
pub mod reparse_all;

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

pub fn make_reflist_of_attachments(
    case: &mut ProcessedGenericDocket,
) -> Vec<&mut ProcessedGenericAttachment> {
    let mut case_refs = Vec::with_capacity(case.filings.len());
    for (_, filling) in case.filings.iter_mut() {
        for (_, attachment) in filling.attachments.iter_mut() {
            case_refs.push(attachment);
        }
    }
    case_refs
}

impl DownloadIncomplete for ProcessedGenericDocket {
    type ExtraData = OpenscrapersExtraData;
    type SucessData = ();
    async fn download_incomplete(
        &mut self,
        extra: &Self::ExtraData,
    ) -> anyhow::Result<Self::SucessData> {
        let attachment_refs = make_reflist_of_attachments(self);
        let wraped_download = async |val: &mut ProcessedGenericAttachment| {
            DownloadIncomplete::download_incomplete(val, extra).await
        };
        let futures_stream = stream::iter(attachment_refs.into_iter().map(wraped_download));
        const CONCURRENT_ATTACHMENTS: usize = 2;
        let _ = futures_stream
            .buffer_unordered(CONCURRENT_ATTACHMENTS)
            .count()
            .await;
        Ok(())
    }
}

pub async fn process_case(
    raw_case: RawGenericDocket,
    extra_data: &OpenscrapersExtraData,
    download_files: bool,
) -> anyhow::Result<()> {
    let (s3_client, jur_info) = extra_data;
    tracing::info!(
        case_num=%raw_case.case_govid,
        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Finished all attachments, pushing case to db."
    );
    let case_address = DocketAddress {
        name: raw_case.case_govid.to_string(),
        jurisdiction: jur_info.to_owned(),
    };
    let s3_result = upload_object(s3_client, &case_address, &raw_case).await;
    if let Err(err) = s3_result {
        tracing::error!(
            case_num=%raw_case.case_govid, 
            %err, 
            state=%jur_info.state,
            jurisdiction=%jur_info.jurisdiction,
            "Failed to push raw case to S3/DB");
        return Err(err);
    }
    let processed_case_cache =
        download_openscrapers_object::<ProcessedGenericDocket>(s3_client, &case_address)
            .await
            .ok();

    let mut processed_case =
        ProcessedGenericDocket::process_from(&raw_case, processed_case_cache.as_ref(), ()).await?;

    if download_files {
        let _ = processed_case.download_incomplete(extra_data).await;
    }

    tracing::info!(
        case_num=%raw_case.case_govid,

        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Successfully pushed case to db."
    );
    Ok(())
}

#[cfg(test)]
mod test;
