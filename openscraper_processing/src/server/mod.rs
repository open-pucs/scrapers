use aide::{
    self,
    axum::{
        ApiRouter, IntoApiResponse,
        routing::{get_with, post_with},
    },
    transform::TransformOperation,
};
use axum::{
    extract::{Path, Query},
    response::{IntoResponse, Json},
};
use hyper::body::Bytes;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::str::FromStr;
use tracing::{error, info, warn};

use crate::types::{
    GenericCase, RawAttachment, env_vars::OPENSCRAPERS_S3_OBJECT_BUCKET, hash::Blake2bHash,
};
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
        )
        .api_route(
            "/admin/read_openscrapers_s3",
            post_with(read_s3_file, read_s3_file_docs),
        )
        .api_route(
            "/admin/write_openscrapers_s3_string",
            post_with(write_s3_file_string, write_s3_file_docs),
        )
        .api_route(
            "/admin/write_openscrapers_s3_json",
            post_with(write_s3_file_json, write_s3_file_docs),
        );

    info!("Routes defined successfully");
    app
}

#[derive(Deserialize, Serialize, JsonSchema)]
struct S3FileLocationParams {
    bucket: Option<String>,
    key: String,
}

async fn read_s3_file(Json(payload): Json<S3FileLocationParams>) -> impl IntoApiResponse {
    let bucket = (payload.bucket)
        .as_deref()
        .unwrap_or(&**OPENSCRAPERS_S3_OBJECT_BUCKET);
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let result = crate::s3_stuff::download_s3_bytes(&s3_client, bucket, &payload.key).await;
    match result {
        Ok(contents) => (axum::http::StatusCode::OK, Bytes::from(contents)).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

fn read_s3_file_docs(op: TransformOperation) -> TransformOperation {
    op.description("Read a file from S3.")
        .response::<200, Bytes>()
        .response_with::<500, String, _>(|res| res.description("Error reading file from S3."))
}

#[derive(Deserialize, Serialize, JsonSchema)]
struct S3UploadString {
    bucket: Option<String>,
    key: String,
    contents: String,
}
async fn write_s3_file_string(Json(payload): Json<S3UploadString>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let contents = payload.contents.into_bytes();
    let bucket = (payload.bucket)
        .as_deref()
        .unwrap_or(&**OPENSCRAPERS_S3_OBJECT_BUCKET);
    let result = crate::s3_stuff::upload_s3_bytes(&s3_client, bucket, &payload.key, contents).await;
    match result {
        Ok(_) => (axum::http::StatusCode::OK).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

#[derive(Deserialize, Serialize, JsonSchema)]
struct S3UploadJson {
    bucket: Option<String>,
    key: String,
    contents: Value,
}
async fn write_s3_file_json(Json(payload): Json<S3UploadJson>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let contents = match serde_json::to_string(&payload.contents) {
        Ok(string) => string.into_bytes(),
        Err(err) => {
            error!("Could not reserialize json value");
            return (axum::http::StatusCode::BAD_REQUEST, err.to_string()).into_response();
        }
    };

    let bucket = (payload.bucket)
        .as_deref()
        .unwrap_or(&**OPENSCRAPERS_S3_OBJECT_BUCKET);
    let result = crate::s3_stuff::upload_s3_bytes(&s3_client, bucket, &payload.key, contents).await;
    match result {
        Ok(_) => (axum::http::StatusCode::OK).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

fn write_s3_file_docs(op: TransformOperation) -> TransformOperation {
    op.description("Write a file to S3.")
        .response::<200, ()>()
        .response_with::<500, String, _>(|res| res.description("Error writing file to S3."))
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
        Ok(contents) => (axum::http::StatusCode::OK, Bytes::from(contents)).into_response(),
        Err(e) => {
            error!(hash = %blake2b_hash,error = %e, "Error reading attachment file from disk");
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
