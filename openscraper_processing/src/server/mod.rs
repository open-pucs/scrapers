use aide::{
    self,
    axum::{
        ApiRouter, IntoApiResponse,
        routing::{get_with, post_with},
    },
    transform::TransformOperation,
};
use axum::response::Json;
use direct_file_fetch::{
    handle_directly_process_file_request, handle_directly_process_file_request_docs,
};
use serde_json::{Value, json};
use tracing::info;

pub mod direct_file_fetch;
pub mod queue_routes;
pub mod s3_routes;

pub fn define_routes() -> ApiRouter {
    println!("Defining API Routes but without tracing.");
    info!("Defining API Routes");
    let app = ApiRouter::new()
        .api_route(
            "/api/cases/{state}/{jurisdiction_name}/{case_name}",
            get_with(
                s3_routes::handle_case_filing_from_s3,
                s3_routes::handle_case_filing_from_s3_docs,
            ),
        )
        .api_route(
            "/api/cases/submit",
            post_with(
                queue_routes::submit_case_to_queue,
                queue_routes::submit_case_to_queue_docs,
            ),
        )
        .api_route(
            "/api/caselist/{state}/{jurisdiction_name}/all",
            get_with(
                s3_routes::handle_caselist_jurisdiction_fetch_all,
                s3_routes::handle_caselist_jurisdiction_fetch_all_docs,
            ),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/obj",
            get_with(
                s3_routes::handle_attachment_data_from_s3,
                s3_routes::handle_attachment_data_from_s3_docs,
            ),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/raw",
            get_with(
                s3_routes::handle_attachment_file_from_s3,
                s3_routes::handle_attachment_file_from_s3_docs,
            ),
        )
        .api_route(
            "/admin/read_openscrapers_s3",
            post_with(s3_routes::read_s3_file, s3_routes::read_s3_file_docs),
        )
        .api_route(
            "/admin/write_openscrapers_s3_string",
            post_with(
                s3_routes::write_s3_file_string,
                s3_routes::write_s3_file_docs,
            ),
        )
        .api_route(
            "/admin/write_openscrapers_s3_json",
            post_with(s3_routes::write_s3_file_json, s3_routes::write_s3_file_docs),
        )
        .api_route(
            "/admin/direct_file_attachment_process",
            post_with(
                handle_directly_process_file_request,
                handle_directly_process_file_request_docs,
            ),
        );

    info!("Routes defined successfully");
    app
}

async fn health() -> impl IntoApiResponse {
    info!("Health check requested");
    let response = json!({"is_healthy": true});
    info!("Health check successful");
    Json(response)
}

fn health_docs(op: TransformOperation) -> TransformOperation {
    op.description("Check the health of the server.")
        .response::<200, Json<Value>>()
}
