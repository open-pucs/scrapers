use aide::{self, axum::IntoApiResponse, transform::TransformOperation};
use axum::response::{IntoResponse, Json};
use openscraper_types::raw::RawDocketWithJurisdiction;
use tracing::info;

use crate::case_worker::ProcessCaseWithoutDownload;

use mycorrhiza_common::tasks::{TaskStatusDisplay, workers::add_task_to_queue};

pub async fn submit_case_to_queue_without_download(
    Json(case): Json<RawDocketWithJurisdiction>,
) -> impl IntoApiResponse {
    let priority = 0;
    info!(case_number = %case.docket.case_govid, %priority, "Request received to submit case to queue");
    let res = add_task_to_queue(ProcessCaseWithoutDownload(case), priority).await;
    (
        axum::http::StatusCode::OK,
        Json(TaskStatusDisplay::from(res)),
    )
        .into_response()
}

pub fn submit_case_to_queue_docs(op: TransformOperation) -> TransformOperation {
    op.description("Submit a case to the processing queue.")
        .response::<200, Json<TaskStatusDisplay>>()
}
