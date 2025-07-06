use aide::axum::ApiRouter;
use axum::{
    extract::{Path, Query, State},
    response::{IntoResponse, Json},
};
use serde::Deserialize;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::info;

use crate::types::{GenericCase, RawAttachment};
use aide::{
    axum::{IntoApiResponse, routing::get},
    openapi::{Info, OpenApi},
    swagger::Swagger,
};

pub async fn define_routes() -> ApiRouter {
    let app = ApiRouter::new()
        .api_route("/api/health", get(health))
        .route(
            "/api/cases/:state/:jurisdiction_name/:case_name",
            get(handle_case_filing_from_s3),
        )
        .route(
            "/api/caselist/:state/:jurisdiction_name/all",
            get(handle_caselist_jurisdiction_fetch_all),
        )
        .route(
            "/api/caselist/:state/:jurisdiction_name/indexed_after/:rfc339_date",
            get(handle_caselist_jurisdiction_fetch_date),
        )
        .route(
            "/api/caselist/all/indexed_after/:rfc339_date",
            get(handle_caselist_all_fetch),
        )
        .route(
            "/api/raw_attachments/:blake2b_hash/obj",
            get(handle_attachment_data_from_s3),
        )
        .route(
            "/api/raw_attachments/:blake2b_hash/raw",
            get(handle_attachment_file_from_s3),
        );
    info!("Routes defined successfully");
    app
}

async fn health() -> impl IntoApiResponse {
    Json("{\"is_healthy\": true}")
}

async fn handle_case_filing_from_s3(
    Path((state, jurisdiction_name, case_name)): Path<(String, String, String)>,
) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}

#[derive(Deserialize)]
struct CaseListParams {
    limit: Option<i32>,
}

async fn handle_caselist_jurisdiction_fetch_all(
    Path((state, jurisdiction_name)): Path<(String, String)>,
) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_caselist_jurisdiction_fetch_date(
    Path((state, jurisdiction_name, rfc339_date)): Path<(String, String, String)>,
) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_caselist_all_fetch(Path(rfc339_date): Path<String>) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_attachment_data_from_s3(Path(blake2b_hash): Path<String>) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_attachment_file_from_s3(Path(blake2b_hash): Path<String>) -> impl IntoApiResponse {
    // TODO: Implement this
    Json("Not implemented")
}
