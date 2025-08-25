use aide::axum::{ApiRouter, IntoApiResponse, routing::post};
use axum::{Json, response::IntoResponse};
use mycorrhiza_common::s3_generic::fetchers_and_getters::S3DirectoryAddr;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::env_vars::OPENSCRAPERS_S3_OBJECT_BUCKET;

pub fn define_temporary_routes(app: ApiRouter) -> ApiRouter {
    app.api_route("/admin/temporary/copy_s3_directory", post(move_s3_objects))
}
#[derive(Deserialize, Serialize, JsonSchema)]
pub struct CopyPrefixRequest {
    delete_after_copy: bool,
    source: S3DirectoryLoc,
    destination: S3DirectoryLoc,
}

#[derive(Deserialize, Serialize, JsonSchema)]
pub struct S3DirectoryLoc {
    bucket: Option<String>,
    prefix: String,
}

pub async fn move_s3_objects(Json(payload): Json<CopyPrefixRequest>) -> impl IntoApiResponse {
    let default_bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let s3_client = crate::s3_stuff::make_s3_client().await;

    let source = S3DirectoryAddr::new(
        &s3_client,
        payload.source.bucket.as_deref().unwrap_or(default_bucket),
        &payload.source.prefix,
    );
    let destination = S3DirectoryAddr::new(
        &s3_client,
        payload
            .destination
            .bucket
            .as_deref()
            .unwrap_or(default_bucket),
        &payload.destination.prefix,
    );

    let result = source.copy_into(&destination).await;

    if result.is_ok() && payload.delete_after_copy {
        source.delete_all().await;
    }

    match result {
        Ok(_) => (axum::http::StatusCode::OK).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}
