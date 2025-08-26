use aide::axum::{
    ApiRouter,
    routing::{delete, post},
};
use axum::Json;
use mycorrhiza_common::s3_generic::fetchers_and_getters::S3DirectoryAddr;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::types::env_vars::OPENSCRAPERS_S3_OBJECT_BUCKET;

pub fn define_temporary_routes(app: ApiRouter) -> ApiRouter {
    app.api_route(
        "/admin/temporary/copy_move_s3_directory",
        post(move_s3_objects),
    )
    .api_route(
        "/admin/temporary/remove_s3_directory",
        delete(delete_s3_objects),
    )
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

pub async fn move_s3_objects(Json(payload): Json<CopyPrefixRequest>) -> Result<(), String> {
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
        let _ = source.delete_all().await;
    }
    result.map_err(|e| e.to_string())
}

pub async fn delete_s3_objects(Json(payload): Json<S3DirectoryLoc>) -> Result<(), String> {
    let default_bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let s3_client = crate::s3_stuff::make_s3_client().await;

    let source = S3DirectoryAddr::new(
        &s3_client,
        payload.bucket.as_deref().unwrap_or(default_bucket),
        &payload.prefix,
    );
    let result = source.delete_all().await;
    result.map_err(|e| e.to_string())
}
