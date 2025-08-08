use std::{collections::HashMap, fmt::Debug, str::FromStr, time::Duration};

use anyhow::{anyhow, bail};
use base64::prelude::*;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;
use tracing::{error, info};

use crate::common::file_extension::FileValidationError;

const DEFAULT_TIMEOUT: Duration = Duration::from_secs(20);

#[derive(Debug, Clone)]
pub struct FileDownloadResult {
    pub data: Vec<u8>,
    pub filename: Option<String>,
}

// Add more data for all of these errors including passing along any internal error values.
#[derive(Debug, Error)]
pub enum FileDownloadError {
    #[error("File download failed with a bad request: {0}")]
    BadRequest(anyhow::Error),
    #[error("File download failed with a rate limit response code")]
    RateLimited,
    #[error("File download failed with a bad request response code: {0}")]
    BadResponseCode(u16),
    #[error("File download returned invalid data: {0}")]
    InvalidReturnData(#[from] FileValidationError),
    #[error("File download failed with a network error: {0}")]
    Network(reqwest::Error),
    #[error("File download timed out: {0}")]
    Timeout(reqwest::Error),
    #[error("File download failed with an unknown error: {0}")]
    Unknown(#[from] anyhow::Error),
}

impl FileDownloadError {
    pub fn is_retryable(&self) -> bool {
        // return true if the error might be solved by retying the request:
        match self {
            Self::BadRequest(_) => false,
            Self::BadResponseCode(_) => false,
            Self::RateLimited => true,
            Self::InvalidReturnData(_) => true,
            Self::Network(_) => true,
            Self::Timeout(_) => true,
            Self::Unknown(_) => false,
        }
    }
}

pub trait InternetFileFetch: Debug {
    // New methods that return filename along with data
    async fn download_file_with_timeout(
        &self,
        timeout: Duration,
    ) -> Result<FileDownloadResult, FileDownloadError>;
    async fn download_file(&self) -> Result<FileDownloadResult, FileDownloadError> {
        self.download_file_with_timeout(DEFAULT_TIMEOUT).await
    }
}

fn extract_filename_from_headers(headers: &reqwest::header::HeaderMap) -> Option<String> {
    // Try to get filename from Content-Disposition header
    if let Some(content_disposition) = headers.get(reqwest::header::CONTENT_DISPOSITION) {
        if let Ok(header_str) = content_disposition.to_str() {
            // Parse Content-Disposition header for filename
            // Common formats:
            // - attachment; filename="file.txt"
            // - attachment; filename*=UTF-8''file.txt
            // - inline; filename=file.txt

            // First try the standard filename parameter
            if let Some(filename_start) = header_str.find("filename=") {
                let filename_part = &header_str[filename_start + 9..];
                let filename = if filename_part.starts_with('"') {
                    // Remove quotes
                    filename_part
                        .trim_start_matches('"')
                        .split('"')
                        .next()
                        .unwrap_or("")
                } else {
                    // Take until semicolon or end
                    filename_part.split(';').next().unwrap_or("").trim()
                };

                if !filename.is_empty() {
                    return Some(filename.to_string());
                }
            }

            // Try filename* parameter (RFC 5987)
            if let Some(filename_start) = header_str.find("filename*=") {
                let filename_part = &header_str[filename_start + 10..];
                // Format is usually: UTF-8''filename or charset'lang'filename
                if let Some(double_quote_pos) = filename_part.find("''") {
                    let filename = &filename_part[double_quote_pos + 2..];
                    let filename = filename.split(';').next().unwrap_or("").trim();
                    if !filename.is_empty() {
                        // URL decode if needed
                        return Some(
                            urlencoding::decode(filename)
                                .unwrap_or_default()
                                .to_string(),
                        );
                    }
                }
            }
        }
    }

    None
}

fn extract_filename_from_url(url: &str) -> Option<String> {
    // Extract filename from URL as fallback
    if let Ok(parsed_url) = url::Url::parse(url) {
        let path = parsed_url.path();
        if let Some(filename) = path.split('/').next_back() {
            if !filename.is_empty() && filename != "/" {
                // Check if there are query parameters that might indicate a filename
                if let Some(query) = parsed_url.query() {
                    if let Some(filename_param) = query
                        .split('&')
                        .find(|param| param.starts_with("fileName="))
                    {
                        let filename = &filename_param[9..]; // Remove "fileName="
                        if !filename.is_empty() {
                            return Some(
                                urlencoding::decode(filename)
                                    .unwrap_or_default()
                                    .to_string(),
                            );
                        }
                    }
                }
                return Some(filename.to_string());
            }
        }
    }
    None
}

impl<T: AsRef<str> + Debug + ?Sized> InternetFileFetch for T {
    async fn download_file_with_timeout(
        &self,
        timeout: Duration,
    ) -> Result<FileDownloadResult, FileDownloadError> {
        let advanced_data = AdvancedFetchData {
            url: self.as_ref().to_owned(),
            headers: None,
            request_body: None,
            request_type: RequestMethod::Get,
        };
        advanced_data.download_file_with_timeout(timeout).await
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema, Default)]
pub enum RequestMethod {
    #[default]
    Get,
    Post,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct AdvancedFetchData {
    pub url: String,
    pub request_type: RequestMethod,
    pub request_body: Option<Value>,
    pub headers: Option<HashMap<String, String>>,
}

impl InternetFileFetch for AdvancedFetchData {
    async fn download_file_with_timeout(
        &self,
        timeout: Duration,
    ) -> Result<FileDownloadResult, FileDownloadError> {
        let client = reqwest::Client::new();

        let mut headers = reqwest::header::HeaderMap::new();
        if let Some(header_hashmap) = &self.headers {
            for (key, value) in header_hashmap {
                let header_name = reqwest::header::HeaderName::from_str(key)
                    .map_err(|_| FileDownloadError::BadRequest(anyhow!("Bad header name")))?;
                let header_value = reqwest::header::HeaderValue::from_str(value)
                    .map_err(|_| FileDownloadError::BadRequest(anyhow!("Bad header value")))?;
                headers.insert(header_name, header_value);
            }
        }

        let request_builder = match self.request_type {
            RequestMethod::Get => client.get(&self.url),
            RequestMethod::Post => client.post(&self.url).json(&self.request_body),
        };

        let response_result = request_builder
            .headers(headers)
            .timeout(timeout)
            .send()
            .await;

        let response = match response_result {
            Ok(res) => res,
            Err(err) => {
                tracing::error!(%err,"Encountered network error getting file.");
                if err.is_timeout() {
                    return Err(FileDownloadError::Timeout(err));
                }
                return Err(FileDownloadError::Network(err));
            }
        };

        let status = response.status();
        if !status.is_success() {
            let err = anyhow::anyhow!(
                "Failed to download file from {}: status code {}",
                self.url,
                response.status()
            );
            return match status.as_u16() {
                400 => Err(FileDownloadError::BadRequest(err)),
                429 => Err(FileDownloadError::RateLimited),
                _ => Err(FileDownloadError::BadResponseCode(status.as_u16())),
            };
        }

        // Extract filename before consuming the response
        let filename = extract_filename_from_headers(response.headers())
            .or_else(|| extract_filename_from_url(&self.url));

        let bytes = response
            .bytes()
            .await
            .map_err(|err| FileDownloadError::Unknown(err.into()))?
            .to_vec();

        if let Some(ref fname) = filename {
            info!("Detected filename: {}", fname);
        }

        Ok(FileDownloadResult {
            data: bytes,
            filename,
        })
    }
}
