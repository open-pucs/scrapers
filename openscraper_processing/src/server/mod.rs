use aide::axum::ApiRouter;
use axum::{
    extract::{Path, Query, State},
    response::{IntoResponse, Json, Response},
};
use hyper::body::Bytes;
use serde::Deserialize;
use std::sync::Arc;
use std::{net::SocketAddr, str::FromStr};
use tokio::sync::Mutex;
use tracing::info;

use crate::types::{GenericCase, RawAttachment, hash::Blake2bHash};
use aide::{
    axum::{IntoApiResponse, routing::get},
    openapi::{Info, OpenApi},
    swagger::Swagger,
};

pub async fn define_routes() -> ApiRouter {
    let app = ApiRouter::new()
        .api_route("/api/health", get(health))
        .api_route(
            "/api/cases/{state}/{jurisdiction_name}/{case_name}",
            get(handle_case_filing_from_s3),
        )
        .api_route(
            "/api/caselist/{state}/{jurisdiction_name}/all",
            get(handle_caselist_jurisdiction_fetch_all),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/obj",
            get(handle_attachment_data_from_s3),
        )
        .api_route(
            "/api/raw_attachments/{blake2b_hash}/raw",
            get(handle_attachment_file_from_s3),
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
    Json("{\"is_healthy\": true}")
}

async fn handle_case_filing_from_s3(
    Path((state, jurisdiction_name, case_name)): Path<(String, String, String)>,
) -> impl IntoApiResponse {
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
        Ok(case) => Json(case).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

#[derive(Deserialize)]
struct CaseListParams {
    limit: Option<i32>,
}

async fn handle_caselist_jurisdiction_fetch_all(
    Path((state, jurisdiction_name)): Path<(String, String)>,
) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let country = "usa"; // Or get from somewhere else
    let result = crate::s3_stuff::list_cases_for_jurisdiction(
        &s3_client,
        &jurisdiction_name,
        &state,
        country,
    )
    .await;
    match result {
        Ok(cases) => Json(cases).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

async fn handle_attachment_data_from_s3(Path(blake2b_hash): Path<String>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let hash = match Blake2bHash::from_str(&blake2b_hash) {
        Ok(hash) => hash,
        Err(e) => {
            return (axum::http::StatusCode::BAD_REQUEST, e.to_string()).into_response();
        }
    };
    let result = crate::s3_stuff::fetch_attachment_data_from_s3(&s3_client, hash).await;
    match result {
        Ok(attachment) => Json(attachment).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

async fn handle_attachment_file_from_s3(Path(blake2b_hash): Path<String>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let hash = match Blake2bHash::from_str(&blake2b_hash) {
        Ok(hash) => hash,
        Err(e) => {
            return (axum::http::StatusCode::BAD_REQUEST, e.to_string()).into_response();
        }
    };
    let result = crate::s3_stuff::fetch_attachment_file_from_s3(&s3_client, hash).await;
    match result {
        Ok(path) => {
            let file_contents = match tokio::fs::read(path).await {
                Ok(contents) => contents,
                Err(e) => {
                    return (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
                        .into_response();
                }
            };
            (axum::http::StatusCode::OK, Bytes::from(file_contents)).into_response()
        }
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
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
