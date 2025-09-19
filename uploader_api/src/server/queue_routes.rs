use aide::{self, axum::IntoApiResponse};
use axum::response::Json;
use futures_util::{future::join_all, join};
use tracing::info;

use crate::case_worker::{
    ProcessCaseWithoutDownload, RawDocketIngestInfo, upload_docket_with_info,
};

use mycorrhiza_common::tasks::{TaskStatusDisplay, workers::add_task_to_queue};

pub async fn submit_cases_to_queue_without_download(
    Json(cases): Json<Vec<RawDocketIngestInfo>>,
) -> impl IntoApiResponse {
    let mut upload_futures = vec![];
    for case_upload_info in cases {
        let govid = case_upload_info.docket.case_govid.as_str();
        let jurisdiction_name = &*case_upload_info.jurisdiction.jurisdiction;
        let upload_type = case_upload_info.upload_type;
        info!(%govid,%jurisdiction_name,?upload_type,"Uploading raw docket");
        upload_futures.push(upload_docket_with_info(case_upload_info));
        // let priority = 0;
        // // let caseid = case_upload_info.docket.case_govid.clone();
        // info!(case_number = %case_upload_info.docket.case_govid, %priority, "Request received to submit case to queue");
        // let status =
        // add_task_to_queue(ProcessCaseWithoutDownload(case_upload_info), priority).await;
        // let display_status = TaskStatusDisplay::from(status);
        // return_results.push(display_status);
    }
    let final_results = join_all(upload_futures).await;
    "Successfully uploaded all cases."
}
