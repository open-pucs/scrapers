use aide::{self, axum::IntoApiResponse, transform::TransformOperation};
use axum::response::{IntoResponse, Json};
use tracing::info;

use crate::{types::CaseWithJurisdiction, worker::push_case_to_queue};

pub async fn submit_case_to_queue(Json(case): Json<CaseWithJurisdiction>) -> impl IntoApiResponse {
    info!(case_number = %case.case.case_number, "Request received to submit case to queue");
    push_case_to_queue(case).await;
    (axum::http::StatusCode::OK).into_response()
}

pub fn submit_case_to_queue_docs(op: TransformOperation) -> TransformOperation {
    op.description("Submit a case to the processing queue.")
        .response::<200, ()>()
}

