use crate::processing::attachments::OpenscrapersExtraData;
use crate::s3_stuff::{fetch_case_filing_from_s3, push_case_to_s3};
use crate::types::data_processing_traits::{DownloadIncomplete, Revalidate, UpdateFromCache};
use crate::types::raw::{
    RawGenericAttachment, RawGenericCase
};
use futures_util::{stream, StreamExt};
use serde::{Deserialize, Serialize};

pub mod attachments;
pub mod file_fetching;
pub mod reparse_all;
pub mod llm_prompts;

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


pub fn make_reflist_of_attachments(case: &mut RawGenericCase) -> Vec<&mut RawGenericAttachment> {
    let mut case_refs= Vec::with_capacity(case.filings.len());
    for filling in case.filings.iter_mut() {
        for attachment in filling.attachments.iter_mut() {
            case_refs.push(attachment);
        }
    }
    case_refs
}

impl DownloadIncomplete for RawGenericCase {
    type ExtraData = OpenscrapersExtraData;
    type SucessData = ();
    async fn download_incomplete(
            &mut self,
            extra: &Self::ExtraData,
        ) -> anyhow::Result<Self::SucessData> {

        let attachment_refs = make_reflist_of_attachments(self);
        let wraped_download = async |val: &mut RawGenericAttachment| {DownloadIncomplete::download_incomplete(val, extra).await};
        let futures_stream = stream::iter(attachment_refs.into_iter().map(wraped_download));
        const CONCURRENT_ATTACHMENTS :usize = 2;
        let _ = futures_stream.buffer_unordered(CONCURRENT_ATTACHMENTS).count().await;
        Ok(())
    }
}


pub async fn process_case(
    mut case: RawGenericCase,
    extra_data: &OpenscrapersExtraData,
    download_files: bool,
) -> anyhow::Result<()> {
    let (s3_client,jur_info) = extra_data;
    case.revalidate();
    // TODO: Fetch data from s3 and merge the cache results.
    let govid = case.case_govid.as_str();
    if let Ok(fetch_from_s3) = fetch_case_filing_from_s3(s3_client, govid, jur_info).await {
        case.update_from_cache(&fetch_from_s3);
    };
    
    if download_files {
        let _ = case.download_incomplete(extra_data).await;
    }

    tracing::info!(
        case_num=%case.case_govid,
        state=%jur_info.state,
        jurisdiction=%jur_info.jurisdiction,
        "Finished all attachments, pushing case to db."
    );
    let s3_result = push_case_to_s3(
        s3_client,
        &case,
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
