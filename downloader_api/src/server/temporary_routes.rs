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

    // FIXME: If this line is commented out this weird fnonce on the higher level function doesnt
    // trigger:
    // 1. implementation of `std::ops::FnOnce` is not general enough
    // closure with signature `fn(&'0 std::string::String) -> {async closure body@mycorrhiza_common::s3_generic::fetchers_and_getters::S3DirectoryAddr<'_>::copy_into::{closure#0}::{closure#0}::{closure#0}<'_>}` must implement `std::ops::FnOnce<(&'1 std::string::String,)>`, for any two lifetimes `'0` and `'1`...
    // ...but it actually implements `std::ops::FnOnce<(&std::string::String,)>`
    //
    // The copy into function is in this file: /home/nicole/Documents/mycorrhiza/common-rs/src/s3_generic/fetchers_and_getters.rs
    let result = source.copy_into(&destination).await;

    todo!();
    // if result.is_ok() && payload.delete_after_copy {
    //     source.delete_all().await;
    // }
    //
    // match result {
    //     Ok(_) => (axum::http::StatusCode::OK).into_response(),
    //     Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    // }
}
