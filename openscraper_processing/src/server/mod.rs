use aide::{
    self,
    axum::{ApiRouter, IntoApiResponse, routing::get_with},
    transform::TransformOperation,
};
use axum::{
    extract::{Path, Query, State},
    response::{IntoResponse, Json, Response},
};
use hyper::body::Bytes;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::{net::SocketAddr, str::FromStr};
use tokio::sync::Mutex;
use tracing::{error, info, warn};

use crate::types::{GenericCase, RawAttachment, hash::Blake2bHash};
// use aide::{
//     axum::{IntoApiResponse, routing::get},
//     openapi::{Info, OpenApi},
//     swagger::Swagger,
// };

#[derive(Deserialize, Serialize, JsonSchema, Default, Clone, Copy)]
struct PaginationData {
    limit: Option<u32>,
    offset: Option<u32>,
}
fn make_paginated_subslice<T>(pagination: PaginationData, slice: &[T]) -> &[T] {
    if pagination.limit.is_none() {
        return slice;
    }
    let begin_index = (pagination.offset.unwrap_or(0) as usize).max(slice.len());
    let end_index = (begin_index + (pagination.limit.unwrap_or(20) as usize)).max(slice.len());
    &slice[begin_index..end_index]
}

pub fn define_routes() -> ApiRouter {
    println!("Defining API Routes but without tracing.");
    info!("Defining API Routes");
    let app = ApiRouter::new()
        .api_route("/api/health", get_with(health, health_docs))
        .api_route(
            "/api/cases/{state}/{jurisdiction_name}/{case_name}",
            get_with(handle_case_filing_from_s3, handle_case_filing_from_s3_docs),
        )
        .api_route(
            "/api/caselist/{state}/{jurisdiction_name}/all",
            get_with(
                handle_caselist_jurisdiction_fetch_all,
                handle_caselist_jurisdiction_fetch_all_docs,
            ),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/obj",
            get_with(
                handle_attachment_data_from_s3,
                handle_attachment_data_from_s3_docs,
            ),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/raw",
            get_with(
                handle_attachment_file_from_s3,
                handle_attachment_file_from_s3_docs,
            ),
        );

    // .api_route(
    //     "/api/caselist/:state/:jurisdiction_name/indexed_after/:rfc339_date",
    //     get(handle_caselist_jurisdiction_fetch_date),
    // )
    // .api_route(
    //     "/api/caselist/all/indexed_after/:rfc339_date",
    //     get(handle_caselist_all_fetch),
    // )
    info!("Routes defined successfully");
    app
}

async fn health() -> impl IntoApiResponse {
    info!("Health check requested");
    let response = Json("{\"is_healthy\": true}");
    info!("Health check successful");
    response
}

fn health_docs(op: TransformOperation) -> TransformOperation {
    op.description("Check the health of the server.")
        .response::<200, Json<String>>()
}

#[derive(Deserialize, JsonSchema)]
struct CasePath {
    /// The state of the jurisdiction.
    state: String,
    /// The name of the jurisdiction.
    jurisdiction_name: String,
    /// The name of the case.
    case_name: String,
}

async fn handle_case_filing_from_s3(
    Path(CasePath {
        state,
        jurisdiction_name,
        case_name,
    }): Path<CasePath>,
) -> impl IntoApiResponse {
    info!(state = %state, jurisdiction = %jurisdiction_name, case = %case_name, "Request received for case filing");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let country = "usa"; // Or get from somewhere else
    let result = crate::s3_stuff::fetch_case_filing_from_s3(
        &s3_client,
        &case_name,
        &jurisdiction_name,
        &state,
        country,
    )
    .await;
    match result {
        Ok(case) => {
            info!(state = %state, jurisdiction = %jurisdiction_name, case = %case_name, "Successfully fetched case filing");
            Json(case).into_response()
        }
        Err(e) => {
            error!(state = %state, jurisdiction = %jurisdiction_name, case = %case_name, error = %e, "Error fetching case filing");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

fn handle_case_filing_from_s3_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch a case filing from S3.")
        .response::<200, Json<GenericCase>>()
        .response_with::<500, String, _>(|res| res.description("Error fetching case filing."))
}

#[derive(Deserialize, JsonSchema)]
struct JurisdictionPath {
    /// The state of the jurisdiction.
    state: String,
    /// The name of the jurisdiction.
    jurisdiction_name: String,
}

#[derive(Deserialize)]
struct CaseListParams {
    limit: Option<i32>,
}

async fn handle_caselist_jurisdiction_fetch_all(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
    Query(PaginationData { limit, offset }): Query<PaginationData>,
) -> impl IntoApiResponse {
    info!(state = %state, jurisdiction = %jurisdiction_name, "Request received for case list");
    warn!("I dont know what the fuck is going wrong with this stuff");
    let s3_client = crate::s3_stuff::make_s3_client().await;

    info!("Sucessfully created s3 client.");
    let country = "usa"; // Or get from somewhere else
    let result = crate::s3_stuff::list_cases_for_jurisdiction(
        &s3_client,
        &jurisdiction_name,
        &state,
        country,
    )
    .await;
    info!("Completed call to s3 to get jurisdiction list.");
    let pagination = PaginationData { limit, offset };
    match result {
        Ok(cases) => {
            info!(state = %state, jurisdiction = %jurisdiction_name, "Successfully fetched case list");
            Json(make_paginated_subslice(pagination, &cases)).into_response()
        }
        Err(e) => {
            error!(state = %state, jurisdiction = %jurisdiction_name, error = %e, "Error fetching case list");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

fn handle_caselist_jurisdiction_fetch_all_docs(op: TransformOperation) -> TransformOperation {
    op.description("List all cases for a jurisdiction.")
        .response::<200, Json<Vec<String>>>()
        .response_with::<500, String, _>(|res| res.description("Error listing cases."))
}

#[derive(Deserialize, JsonSchema)]
struct AttachmentPath {
    /// The blake2b hash of the attachment.
    blake2b_hash: String,
}

async fn handle_attachment_data_from_s3(
    Path(AttachmentPath { blake2b_hash }): Path<AttachmentPath>,
) -> impl IntoApiResponse {
    info!(hash = %blake2b_hash, "Request received for attachment data");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let hash = match Blake2bHash::from_str(&blake2b_hash) {
        Ok(hash) => hash,
        Err(e) => {
            error!(hash = %blake2b_hash, error = %e, "Invalid hash format for attachment data request");
            return (axum::http::StatusCode::BAD_REQUEST, e.to_string()).into_response();
        }
    };
    let result = crate::s3_stuff::fetch_attachment_data_from_s3(&s3_client, hash).await;
    match result {
        Ok(attachment) => {
            info!(hash = %blake2b_hash, "Successfully fetched attachment data");
            Json(attachment).into_response()
        }
        Err(e) => {
            error!(hash = %blake2b_hash, error = %e, "Error fetching attachment data");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

fn handle_attachment_data_from_s3_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch attachment data from S3.")
        .response::<200, Json<RawAttachment>>()
        .response_with::<400, String, _>(|res| res.description("Invalid hash format."))
        .response_with::<500, String, _>(|res| res.description("Error fetching attachment data."))
}

async fn handle_attachment_file_from_s3(
    Path(AttachmentPath { blake2b_hash }): Path<AttachmentPath>,
) -> impl IntoApiResponse {
    info!(hash = %blake2b_hash, "Request received for attachment file");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let hash = match Blake2bHash::from_str(&blake2b_hash) {
        Ok(hash) => hash,
        Err(e) => {
            error!(hash = %blake2b_hash, error = %e, "Invalid hash format for attachment file request");
            return (axum::http::StatusCode::BAD_REQUEST, e.to_string()).into_response();
        }
    };
    let result = crate::s3_stuff::fetch_attachment_file_from_s3(&s3_client, hash).await;
    match result {
        Ok(path) => {
            let file_contents = match tokio::fs::read(&path).await {
                Ok(contents) => contents,
                Err(e) => {
                    error!(hash = %blake2b_hash, path = ?path, error = %e, "Error reading attachment file from disk");
                    return (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
                        .into_response();
                }
            };
            info!(hash = %blake2b_hash, "Successfully fetched attachment file");
            (axum::http::StatusCode::OK, Bytes::from(file_contents)).into_response()
        }
        Err(e) => {
            error!(hash = %blake2b_hash, error = %e, "Error fetching attachment file");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

fn handle_attachment_file_from_s3_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch an attachment file from S3.")
        .response::<200, Bytes>()
        .response_with::<400, String, _>(|res| res.description("Invalid hash format."))
        .response_with::<500, String, _>(|res| res.description("Error fetching attachment file."))
}

// async fn handle_caselist_jurisdiction_fetch_date(
//     Path((state, jurisdiction_name, rfc339_date)): Path<(String, String, String)>,
// ) -> impl IntoApiResponse {
//     // TODO: Implement this
//     Json("Not implemented")
// }
//
// async fn handle_caselist_all_fetch(Path(rfc339_date): Path<String>) -> impl IntoApiResponse {
//     // TODO: Implement this
//     Json("Not implemented")
// }
