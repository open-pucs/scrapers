use axum::{
    extract::{Path, Query, State},
    response::{IntoResponse, Json},
    routing::get,
    Router,
};
use serde::Deserialize;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::types::{GenericCase, RawAttachment};

struct AppState {
    // We can add any shared state here, like a database connection pool
}

pub async fn start_server() {
    let shared_state = Arc::new(Mutex::new(AppState {}));

    let app = Router::new()
        .route("/api/health", get(health))
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
        )
        .with_state(shared_state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn health() -> impl IntoResponse {
    Json("{\"is_healthy\": true}")
}

async fn handle_case_filing_from_s3(
    Path((state, jurisdiction_name, case_name)): Path<(String, String, String)>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}

#[derive(Deserialize)]
struct CaseListParams {
    limit: Option<i32>,
}

async fn handle_caselist_jurisdiction_fetch_all(
    Path((state, jurisdiction_name)): Path<(String, String)>,
    Query(params): Query<CaseListParams>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_caselist_jurisdiction_fetch_date(
    Path((state, jurisdiction_name, rfc339_date)): Path<(String, String, String)>,
    Query(params): Query<CaseListParams>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_caselist_all_fetch(
    Path(rfc339_date): Path<String>,
    Query(params): Query<CaseListParams>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_attachment_data_from_s3(
    Path(blake2b_hash): Path<String>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}

async fn handle_attachment_file_from_s3(
    Path(blake2b_hash): Path<String>,
    State(_state): State<Arc<Mutex<AppState>>>,
) -> impl IntoResponse {
    // TODO: Implement this
    Json("Not implemented")
}
