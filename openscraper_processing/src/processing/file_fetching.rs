use std::{collections::HashMap, fmt::Debug, str::FromStr, time::Duration};

use anyhow::bail;
use base64::prelude::*;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::{error, info};

const DEFAULT_TIMEOUT: Duration = Duration::from_secs(20);

pub trait InternetFileFetch: Debug {
    async fn download_file_with_timeout(&self, timeout: Duration) -> anyhow::Result<Vec<u8>>;
    async fn download_file(&self) -> anyhow::Result<Vec<u8>> {
        self.download_file_with_timeout(DEFAULT_TIMEOUT).await
    }
}
impl<T: AsRef<str> + Debug + ?Sized> InternetFileFetch for T {
    async fn download_file_with_timeout(&self, timeout: Duration) -> anyhow::Result<Vec<u8>> {
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

        let bytes = response.bytes().await?.to_vec();
        info!("Successfully downloaded {} bytes", bytes.len());
        Ok(bytes)
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
    async fn download_file_with_timeout(&self, timeout: Duration) -> anyhow::Result<Vec<u8>> {
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

        let bytes = response.bytes().await?;
        let decoded_bytes = match self.decode_method {
            InternetDecodeMethod::None => bytes.to_vec(),
            InternetDecodeMethod::Base64Regular => BASE64_STANDARD.decode(&bytes)?,
            InternetDecodeMethod::Base64UrlSafe => BASE64_URL_SAFE.decode(&bytes)?,
        };
        Ok(decoded_bytes.to_vec())
    }
}
