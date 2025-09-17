use aide::{self, axum::IntoApiResponse, transform::TransformOperation};
use axum::response::{IntoResponse, Json};
use openscraper_types::{
    jurisdictions::JurisdictionInfo,
    raw::{RawDocketWithJurisdiction, RawGenericDocket},
};
use serde::{Deserialize, Serialize};
use tracing::info;

use crate::case_worker::{
    ProcessCaseWithoutDownload, RawDocketIngestInfo, upload_docket_with_info,
};

use mycorrhiza_common::tasks::{TaskStatusDisplay, workers::add_task_to_queue};

pub async fn submit_cases_to_queue_without_download(
    Json(cases): Json<Vec<RawDocketIngestInfo>>,
) -> impl IntoApiResponse {
    let mut return_results = vec![];
    for case_upload_info in cases {
        let priority = 0;
        let caseid = case_upload_info.docket.case_govid.clone();
        info!(case_number = %case_upload_info.docket.case_govid, %priority, "Request received to submit case to queue");
        let status = add_task_to_queue(ProcessCaseWithoutDownload(case), priority).await;
        let display_status: TaskStatusDisplay = status.into();
        return_results.push(TaskStatusDisplay::from(display_status));
        // let val = upload_docket_with_info(case_upload_info).await;
        // let return_string = match val {
        //     Ok(_) => format!("Docket {caseid} was uploaded successfully"),
        //     Err(err) => format!("Docket {caseid} encountered an error: {err}"),
        // };
        // return_results.push(return_string);
    }
    Json(return_results)
}
