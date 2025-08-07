use aide::{axum::IntoApiResponse, transform::TransformOperation};
use axum::{Json, response::IntoResponse};

use crate::{
    processing::attachments::{
        DirectAttachmentProcessInfo, DirectAttachmentReturnInfo,
        process_attachment_with_direct_request,
    },
    types::RawAttachment,
};

pub async fn handle_directly_process_file_request(
    Json(direct_info): Json<DirectAttachmentProcessInfo>,
) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let attach_res = process_attachment_with_direct_request(&direct_info, s3_client).await;
    match attach_res {
        Ok(val) => (axum::http::StatusCode::OK, Json(val)).into_response(),
        Err(err) => (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            err.to_string(),
        )
            .into_response(),
    }
}

pub fn handle_directly_process_file_request_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch attachment data from S3.")
        .response::<200, Json<DirectAttachmentReturnInfo>>()
        .response_with::<400, String, _>(|res| res.description("Invalid format"))
        .response_with::<500, String, _>(|res| res.description("Error processing attachment data"))
}
