use std::{collections::HashMap, fmt::Debug, str::FromStr, time::Duration};

use anyhow::bail;
use base64::prelude::*;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::{error, info};

const DEFAULT_TIMEOUT: Duration = Duration::from_secs(20);

#[derive(Debug, Clone)]
pub struct FileDownloadResult {
    pub data: Vec<u8>,
    pub filename: Option<String>,
}

pub trait InternetFileFetch: Debug {
    // New methods that return filename along with data
    async fn download_file_with_timeout(
        &self,
        timeout: Duration,
    ) -> anyhow::Result<FileDownloadResult>;
    async fn download_file(&self) -> anyhow::Result<FileDownloadResult> {
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
    ) -> anyhow::Result<FileDownloadResult> {
        let self_str = self.as_ref();
        info!(self_str, "Downloading file");
        let client = reqwest::Client::new();
        let response_result = client.get(self_str).timeout(timeout).send().await;

        let response = match response_result {
            Ok(res) => res,
            Err(err) => {
                tracing::error!(%err,"Encountered network error getting file.");
                return Err(anyhow::Error::from(err));
            }
        };

        if !response.status().is_success() {
            let status = response.status();
            let error_msg = format!("HTTP request failed with status code: {status}");
            error!(url=self_str, %status, "Download failed");
            bail!(error_msg);
        }

        // Extract filename before consuming the response
        let filename = extract_filename_from_headers(response.headers())
            .or_else(|| extract_filename_from_url(self_str));

        let bytes = response.bytes().await?.to_vec();
        info!("Successfully downloaded {} bytes", bytes.len());

        if let Some(ref fname) = filename {
            info!("Detected filename: {}", fname);
        }

        Ok(FileDownloadResult {
            data: bytes,
            filename,
        })
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema, Default)]
enum RequestMethod {
    #[default]
    Get,
    Post,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct AdvancedFetchData {
    url: String,
    request_type: RequestMethod,
    request_body: Option<Value>,
    headers: Option<HashMap<String, String>>,
    decode_method: InternetDecodeMethod,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema, Default)]
pub enum InternetDecodeMethod {
    #[default]
    None,
    Base64Regular,
    Base64UrlSafe,
}

impl InternetFileFetch for AdvancedFetchData {
    async fn download_file_with_timeout(
        &self,
        timeout: Duration,
    ) -> anyhow::Result<FileDownloadResult> {
        let client = reqwest::Client::new();

        let mut headers = reqwest::header::HeaderMap::new();
        if let Some(header_hashmap) = &self.headers {
            for (key, value) in header_hashmap {
                let header_name = reqwest::header::HeaderName::from_str(key)?;
                let header_value = reqwest::header::HeaderValue::from_str(value)?;
                headers.insert(header_name, header_value);
            }
        }

        let request_builder = match self.request_type {
            RequestMethod::Get => client.get(&self.url),
            RequestMethod::Post => client.post(&self.url).json(&self.request_body),
        };

        let response = request_builder
            .headers(headers)
            .timeout(timeout)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!(
                "Failed to download file from {}: status code {}",
                self.url,
                response.status()
            ));
        }

        // Extract filename before consuming the response
        let filename = extract_filename_from_headers(response.headers())
            .or_else(|| extract_filename_from_url(&self.url));

        let bytes = response.bytes().await?;
        let decoded_bytes = match self.decode_method {
            InternetDecodeMethod::None => bytes.to_vec(),
            InternetDecodeMethod::Base64Regular => BASE64_STANDARD.decode(&bytes)?,
            InternetDecodeMethod::Base64UrlSafe => BASE64_URL_SAFE.decode(&bytes)?,
        };

        if let Some(ref fname) = filename {
            info!("Detected filename: {}", fname);
        }

        Ok(FileDownloadResult {
            data: decoded_bytes,
            filename,
        })
    }
}
