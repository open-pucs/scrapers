use aide::{self, axum::IntoApiResponse, transform::TransformOperation};
use axum::{
    extract::{Path, Query},
    http::HeaderValue,
    response::{IntoResponse, Json},
};
use hyper::{StatusCode, body::Bytes, header};
use mycorrhiza_common::{
    hash::Blake2bHash,
    s3_generic::fetchers_and_getters::{S3Addr, S3DirectoryAddr},
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::str::FromStr;
use tracing::{error, info};

use crate::{
    s3_stuff::{
        DocketAddress, delete_openscrapers_s3_object, download_openscrapers_object,
        get_jurisdiction_prefix, list_cases_for_jurisdiction,
    },
    types::{
        env_vars::OPENSCRAPERS_S3_OBJECT_BUCKET,
        jurisdictions::JurisdictionInfo,
        pagination::{PaginationData, make_paginated_subslice},
        processed::ProcessedGenericDocket,
        raw::{RawAttachment, RawGenericDocket},
    },
};

#[derive(Deserialize, Serialize, JsonSchema)]
pub struct OpenscrapersS3Path {
    pub path: String,
}
pub async fn read_openscrapers_s3_file(
    Path(OpenscrapersS3Path { path }): Path<OpenscrapersS3Path>,
) -> impl IntoApiResponse {
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let result = S3Addr::new(&s3_client, bucket, &path)
        .download_bytes()
        .await;
    match result {
        Ok(contents) => (axum::http::StatusCode::OK, Bytes::from(contents)).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

pub fn read_s3_file_docs(op: TransformOperation) -> TransformOperation {
    op.description("Read a file from S3.")
        .response::<200, Bytes>()
        .response_with::<500, String, _>(|res| res.description("Error reading file from S3."))
}

#[derive(Deserialize, Serialize, JsonSchema)]
pub struct S3UploadString {
    bucket: Option<String>,
    key: String,
    contents: String,
}
pub async fn write_s3_file_string(Json(payload): Json<S3UploadString>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let contents = payload.contents.into_bytes();
    let bucket = (payload.bucket)
        .as_deref()
        .unwrap_or(&**OPENSCRAPERS_S3_OBJECT_BUCKET);
    let result = S3Addr::new(&s3_client, bucket, &payload.key)
        .upload_bytes(contents)
        .await;
    match result {
        Ok(_) => (axum::http::StatusCode::OK).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

#[derive(Deserialize, Serialize, JsonSchema)]
pub struct S3UploadJson {
    bucket: Option<String>,
    key: String,
    contents: Value,
}
pub async fn write_s3_file_json(Json(payload): Json<S3UploadJson>) -> impl IntoApiResponse {
    let s3_client = crate::s3_stuff::make_s3_client().await;

    let bucket = (payload.bucket)
        .as_deref()
        .unwrap_or(&**OPENSCRAPERS_S3_OBJECT_BUCKET);
    let result = S3Addr::new(&s3_client, bucket, &payload.key)
        .upload_json(&payload.contents)
        .await;
    match result {
        Ok(_) => (axum::http::StatusCode::OK).into_response(),
        Err(e) => (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

pub fn write_s3_file_docs(op: TransformOperation) -> TransformOperation {
    op.description("Write a file to S3.")
        .response::<200, ()>()
        .response_with::<500, String, _>(|res| res.description("Error writing file to S3."))
}

#[derive(Deserialize, JsonSchema)]
pub struct CasePath {
    /// The state of the jurisdiction.
    state: String,
    /// The name of the jurisdiction.
    jurisdiction_name: String,
    /// The name of the case.
    case_name: String,
}

pub async fn handle_processed_case_filing_from_s3(
    Path(CasePath {
        state,
        jurisdiction_name,
        case_name,
    }): Path<CasePath>,
) -> Result<Json<ProcessedGenericDocket>, String> {
    info!(state = %state, jurisdiction = %jurisdiction_name, case = %case_name, "Request received for case filing");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let jurisdiction_info = JurisdictionInfo::new_usa(&jurisdiction_name, &state);
    let addr_info = DocketAddress {
        jurisdiction: jurisdiction_info,
        name: case_name,
    };
    let result = download_openscrapers_object(&s3_client, &addr_info).await;
    match result {
        Ok(case) => {
            info!(state = %state, jurisdiction = %jurisdiction_name, case = %addr_info.name, "Successfully fetched case filing");
            Ok(Json(case))
        }
        Err(e) => {
            error!(state = %state, jurisdiction = %jurisdiction_name, case = %addr_info.name, error = %e, "Error fetching case filing");
            Err(e.to_string())
        }
    }
}

pub async fn delete_case_filing_from_s3(
    Path(CasePath {
        state,
        jurisdiction_name,
        case_name,
    }): Path<CasePath>,
) -> impl IntoApiResponse {
    info!(state = %state, jurisdiction = %jurisdiction_name, case = %case_name, "Request received to delete case filing");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let jurisdiction_info = JurisdictionInfo::new_usa(&jurisdiction_name, &state);

    let addr_info = DocketAddress {
        jurisdiction: jurisdiction_info,
        name: case_name,
    };
    let result =
        delete_openscrapers_s3_object::<ProcessedGenericDocket>(&s3_client, &addr_info).await;
    match result {
        Ok(_) => {
            info!(state = %state, jurisdiction = %jurisdiction_name, case = %addr_info.name, "Successfully deleted case filing");
            StatusCode::NO_CONTENT.into_response()
        }
        Err(e) => {
            error!(state = %state, jurisdiction = %jurisdiction_name, case = %addr_info.name, error = %e, "Error deleting case filing");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

pub async fn recursive_delete_all_jurisdiction_data(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
) -> impl IntoApiResponse {
    info!(state = %state, jurisdiction = %jurisdiction_name, "Deleting all data for jurisdiction");
    let s3_client = crate::s3_stuff::make_s3_client().await;
    let jurisdiction_info = JurisdictionInfo::new_usa(&jurisdiction_name, &state);
    let prefix = get_jurisdiction_prefix(&jurisdiction_info);
    let bucket = &**OPENSCRAPERS_S3_OBJECT_BUCKET;
    let result = S3DirectoryAddr::new(&s3_client, bucket, &prefix)
        .delete_all()
        .await;
    match result {
        Ok(_) => {
            info!(state = %state, jurisdiction = %jurisdiction_name, "Successfully deleted all jurisdiction data");
            StatusCode::NO_CONTENT.into_response()
        }
        Err(e) => {
            error!(state = %state, jurisdiction = %jurisdiction_name, error = %e, "Error deleting all jurisdiction data");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

#[derive(Deserialize, JsonSchema)]
pub struct JurisdictionPath {
    /// The state of the jurisdiction.
    pub state: String,
    /// The name of the jurisdiction.
    pub jurisdiction_name: String,
}

pub async fn handle_caselist_jurisdiction_fetch_all(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
    Query(PaginationData { limit, offset }): Query<PaginationData>,
) -> impl IntoApiResponse {
    info!(state = %state, jurisdiction = %jurisdiction_name, "Request received for case list");
    let s3_client = crate::s3_stuff::make_s3_client().await;

    info!("Sucessfully created s3 client.");
    let country = "usa".to_string(); // Or get from somewhere else
    let jur_info = JurisdictionInfo {
        state,
        country,
        jurisdiction: jurisdiction_name,
    };
    let result = list_cases_for_jurisdiction(&s3_client, &jur_info).await;
    info!("Completed call to s3 to get jurisdiction list.");
    let pagination = PaginationData { limit, offset };
    match result {
        Ok(cases) => {
            info!(state = %jur_info.state, jurisdiction = %jur_info.jurisdiction, "Successfully fetched case list");
            Json(make_paginated_subslice(pagination, &cases)).into_response()
        }
        Err(e) => {
            error!(state = %jur_info.state, jurisdiction = %jur_info.jurisdiction, error = %e, "Error fetching case list");
            (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()
        }
    }
}

pub fn handle_caselist_jurisdiction_fetch_all_docs(op: TransformOperation) -> TransformOperation {
    op.description("List all cases for a jurisdiction.")
        .response::<200, Json<Vec<String>>>()
        .response_with::<500, String, _>(|res| res.description("Error listing cases."))
}

#[derive(Deserialize, JsonSchema)]
pub struct AttachmentPath {
    /// The blake2b hash of the attachment.
    blake2b_hash: String,
}

pub async fn handle_attachment_data_from_s3(
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
    let result = download_openscrapers_object::<RawAttachment>(&s3_client, &hash).await;
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

pub fn handle_attachment_data_from_s3_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch attachment data from S3.")
        .response::<200, Json<RawAttachment>>()
        .response_with::<400, String, _>(|res| res.description("Invalid hash format."))
        .response_with::<500, String, _>(|res| res.description("Error fetching attachment data."))
}

pub async fn handle_attachment_file_from_s3(
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
    let result =
        crate::s3_stuff::fetch_attachment_file_from_s3_with_filename(&s3_client, hash).await;
    match result {
        Ok((filename, contents)) => {
            // Content‑Type – generic binary stream
            let ct = HeaderValue::from_static("application/octet-stream");

            // Content‑Disposition – attachment; filename="<sanitized>"
            let escaped_name = urlencoding::encode(&filename);
            let cd = format!(
                "attachment; filename=\"{}\"; filename*=UTF-8''{}",
                // Legacy (ASCII‑only) fallback – we keep the original name but
                // escape any double‑quotes or backslashes.
                filename.replace('\\', "\\\\").replace('\"', "\\\""),
                escaped_name
            );
            let cd = HeaderValue::from_str(&cd).expect("valid header value");

            // Optional: Content‑Length – helps the client know the exact size
            let cl = HeaderValue::from_str(&contents.len().to_string())
                .expect("content length is a valid integer");

            // ---------------------------------------------------------------
            //   3b️⃣ Return the tuple that Axum knows how to turn into a response
            // ---------------------------------------------------------------
            (
                StatusCode::OK,
                // An array of header‑name / header‑value pairs.
                // You can add more if you need (Cache‑Control, ETag, …)
                [
                    (header::CONTENT_TYPE, ct),
                    (header::CONTENT_DISPOSITION, cd),
                    (header::CONTENT_LENGTH, cl),
                ],
                // The body – we turn the Vec<u8> (or whatever `contents` is) into Bytes.
                Bytes::from(contents),
            )
                .into_response()
        }
        Err(e) => {
            error!(hash = %blake2b_hash,error = %e, "Error reading attachment file from disk");
            (axum::http::StatusCode::NOT_FOUND, e.to_string()).into_response()
        }
    }
}

pub fn handle_attachment_file_from_s3_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch an attachment file from S3.")
        .response::<200, Bytes>()
        .response_with::<400, String, _>(|res| res.description("Invalid hash format."))
        .response_with::<500, String, _>(|res| res.description("Error fetching attachment file."))
}
