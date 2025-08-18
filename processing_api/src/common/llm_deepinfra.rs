use serde::{Deserialize, Serialize};
use std::env;
use std::fmt::Debug;
use std::sync::LazyLock;

use crate::common::misc::fmap_empty;

pub static DEEPINFRA_API_KEY: LazyLock<String> =
    LazyLock::new(|| env::var("DEEPINFRA_API_KEY").expect("Expected DEEPINFRA_API_KEY"));

pub const FAST_CHEAP_MODEL_NAME: &str = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-Turbo";
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
    simple_prompt(FAST_CHEAP_MODEL_NAME, Some(sys_prompt), None).await
}

pub async fn reasoning_prompt(sys_prompt: &str) -> Result<String, DeepInfraError> {
    simple_prompt(REASONING_MODEL_NAME, Some(sys_prompt), None).await
}

pub async fn org_split_from_dump(org_dump: &str) -> anyhow::Result<Vec<String>> {
    let prompt = format!(
        r#"We have an unformatted list of individuals and or organizations, try and parse them out as a json serializable list of organizations like so, we are also trying to match the organizations on their name, so removing the variable suffixes is important as well. YOUR RESPONSE MUST BE JSON SERIALIZABLE AND CONTAIN NO OTHER TEXT:
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
        tracing::info!(previous_name=%first_el, new_list =?llm_parsed_names,"Parsed list into a bunch of llm names.");
        *auth_list = llm_parsed_names
    }
}

pub async fn guess_at_filling_title<T: AsRef<str> + Serialize>(attachment_names: &[T]) -> String {
    if attachment_names.len() == 1
        && let Some(first) = attachment_names.first()
    {
        return first.as_ref().to_string();
    };
    let Ok(serialized_attach_names) = serde_json::to_string(attachment_names) else {
        return "".to_string();
    };

    let prompt = format!(
        r#"There is a filling consisting of a bunch of attachment with names given below, come up with a good sensible guess for what the entire filling should be named. In general it should be the name of the most important filling in the attachment
ONLY RETURN THE SUGGESTED NAME RETURN NO OTHER TEXT:

Example 1:
["Notice of Minor Changes to Compliance Filing", "Notice of Minor Changes to Compliance Filing"]
Response 1:
Notice of Minor Changes to Compliance Filing
Example 2:
["C-8003CF.pdf", "C-8002CF.pdf", "C-8001CF.pdf", "C-8000CF.pdf", "Bikeway Design.pdf", "Bikeway Cover Letter.pdf"]
Response 2:
Bikeway Design
Example 3:
["Empire Decommissioning 2022 Addendum", "Cover Letter"]
Response 3:
Empire Decommissioning 2022 Addendum
Example 3:
["Empire Generating submits cover letter and drawing C-1002 which indicates the details of Empire Generating's driveway turn control design.", "Drawing C-1002"]
Response 4:
Empire Generating Driveway Turn Control Design C-1002
Example 5:
["Cover Letter", "BOS-PF-24-30 Empire Decommissioning Review - Main", "BOS-PF-24-30 Empire Decommissioning Review - Appendix 1", "BOS-PF-24-30 Empire Decommissioning Review - Appendix 2"]
Response 6:
BOS-PF-24-30 Empire Decommissioning Review

Attachment Names:
{serialized_attach_names}
Response:
"#
    );
    let guess = cheap_prompt(&prompt).await.unwrap_or("".to_string());

    tracing::info!(%guess, initial_names=?serialized_attach_names,"Guesing at attachment title");
    guess
}

fn strip_think(input: &str) -> &str {
    input.split("</think>").last().unwrap_or(input).trim()
}

pub async fn test_deepinfra() -> Result<String, String> {
    cheap_prompt("What is your favorite color?")
        .await
        .map_err(|e| e.to_string())
}
