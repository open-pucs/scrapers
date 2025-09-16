use aide::{self, axum::IntoApiResponse, transform::TransformOperation};
use axum::response::{IntoResponse, Json};
use openscraper_types::{
    jurisdictions::JurisdictionInfo,
    raw::{RawDocketWithJurisdiction, RawGenericDocket},
};
use serde::{Deserialize, Serialize};
use tracing::info;

use crate::case_worker::{ProcessCaseWithoutDownload, RawDocketIngestInfo};

use mycorrhiza_common::tasks::{TaskStatusDisplay, workers::add_task_to_queue};

pub async fn submit_cases_to_queue_without_download(
    Json(cases): Json<Vec<RawDocketIngestInfo>>,
) -> impl IntoApiResponse {
    let mut return_results = vec![];
    for case in cases {
        let priority = 0;
        info!(case_number = %case.docket.case_govid, %priority, "Request received to submit case to queue");
        let res = add_task_to_queue(ProcessCaseWithoutDownload(case), priority).await;
        return_results.push(TaskStatusDisplay::from(res));
    }
    (axum::http::StatusCode::OK, Json(return_results)).into_response()
}

pub fn submit_case_to_queue_docs(op: TransformOperation) -> TransformOperation {
    op.description("Submit a case to the processing queue.")
        .response::<200, Json<TaskStatusDisplay>>()
}
