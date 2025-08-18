use serde::{Deserialize, Serialize};
use std::env;
use std::sync::LazyLock;

use crate::common::misc::fmap_empty;

pub static DEEPINFRA_API_KEY: LazyLock<String> =
    LazyLock::new(|| env::var("DEEPINFRA_API_KEY").expect("Expected DEEPINFRA_API_KEY"));

pub const CHEAP_MODEL_NAME: &str = "Qwen/Qwen3-32B";
pub const REASONING_MODEL_NAME: &str = "meta-llama/Meta-Llama-3-70B-Instruct";

#[derive(Debug, thiserror::Error)]
pub enum DeepInfraError {
    #[error("HTTP request failed: {0}")]
    Reqwest(#[from] reqwest::Error),
    #[error("Failed to deserialize response: {0}")]
    Serde(#[from] serde_json::Error),
    #[error("API returned an error: {0}")]
    ApiError(String),
    #[error("No choices returned from API")]
    NoChoices,
}

#[derive(Serialize)]
struct DeepInfraRequestBody {
    model: &'static str,
    messages: Vec<DeepInfraMessage>,
}

#[derive(Serialize, Deserialize)]
struct DeepInfraMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct DeepInfraResponseBody {
    choices: Vec<DeepInfraChoice>,
    usage: DeepInfraResponseUsage,
}

#[derive(Deserialize)]
struct DeepInfraChoice {
    message: DeepInfraMessage,
}

#[derive(Deserialize)]
struct DeepInfraResponseUsage {
    prompt_tokens: u32,
    completion_tokens: u32,
    total_tokens: u32,
}

async fn simple_prompt(
    model_name: &'static str,
    system_prompt: Option<&str>,
    user_prompt: Option<&str>,
) -> Result<String, DeepInfraError> {
    let client = reqwest::Client::new();

    let mut messages = Vec::new();
    if let Some(sys_prompt) = fmap_empty(system_prompt) {
        messages.push(DeepInfraMessage {
            role: "system".into(),
            content: sys_prompt.into(),
        });
    }
    if let Some(usr_prompt) = fmap_empty(user_prompt) {
        messages.push(DeepInfraMessage {
            role: "user".into(),
            content: usr_prompt.into(),
        });
    }

    let request_body = DeepInfraRequestBody {
        model: model_name,
        messages,
    };

    let response = client
        .post("https://api.deepinfra.com/v1/openai/chat/completions")
        .header("Authorization", format!("Bearer {}", *DEEPINFRA_API_KEY))
        .json(&request_body)
        .send()
        .await?;

    if !response.status().is_success() {
        let error_body = response.text().await?;
        return Err(DeepInfraError::ApiError(error_body));
    }

    let response_body: DeepInfraResponseBody = response.json().await?;

    if let Some(choice) = response_body.choices.into_iter().next() {
        Ok(choice.message.content.to_string())
    } else {
        Err(DeepInfraError::NoChoices)
    }
}

pub async fn cheap_prompt(sys_prompt: &str) -> Result<String, DeepInfraError> {
    simple_prompt(CHEAP_MODEL_NAME, Some(sys_prompt), None).await
}

pub async fn reasoning_prompt(sys_prompt: &str) -> Result<String, DeepInfraError> {
    simple_prompt(REASONING_MODEL_NAME, Some(sys_prompt), None).await
}

pub async fn org_split_from_dump(org_dump: &str) -> anyhow::Result<Vec<String>> {
    let prompt = format!(
        r#"We have an unformatted list of individuals and or organizations, try and parse them out as a json serializable list of organizations like so, we are also trying to match the organizations on their name, so removing the variable suffixes is important as well::
Example 1:
Manhattan Telecommunications Corporation LLC d/b/a Metropolitan Communications Solutions, LLC
Response 1:
["Manhattan Telecommunications Corporation"]

Example 2:
Dunkirk and Fredonia Telephone Company, Niagara Mohawk Energy Marketing
Response 2:
["Dunkirk and Fredonia Telephone Company", "Niagara Mohawk Energy Marketing"]

Example 3:
Broadview Networks, Inc., CTC Communications Corp., Conversent Communications of New York, LLC, Eureka Telecom, Inc., PAETEC Communications, LLC, US LEC Communications, Inc.
Response 3:
["Broadview Networks","CTC Communications", "Conversent Communications of New York", "Eureka Telecom", "PAETEC Communications","US LEC Communications"]

Example 4:
City of Salamanca Board of Public Utilities
Response 4:
["City of Salamanca Board of Public Utilities"]

Example 5:
LS Power Grid New York Corporation I, Niagara Mohawk Power Corporation d/b/a National Grid
Response 5:
["LS Power Grid New York Corporation I", "Niagara Mohawk Power Corporation"]

Final:
{org_dump}
Response:
"#
    );
    let result = cheap_prompt(&prompt).await.map_err(anyhow::Error::from)?;
    let json_res = serde_json::from_slice::<Vec<String>>(strip_think(&result).as_bytes());
    json_res.map_err(anyhow::Error::from)
}

pub async fn split_mutate_author_list(auth_list: &mut Vec<String>) {
    if auth_list.len() == 1
        && let Some(first_el) = auth_list.first()
    {
        let Ok(llm_parsed_names) = org_split_from_dump(first_el).await else {
            return;
        };

        *auth_list = llm_parsed_names
    }
}

fn strip_think(input: &str) -> &str {
    input.split("</think>").last().unwrap_or(input).trim()
}

pub async fn test_deepinfra() -> Result<String, String> {
    cheap_prompt("What is your favorite color?")
        .await
        .map_err(|e| e.to_string())
}

