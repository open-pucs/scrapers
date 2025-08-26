use mycorrhiza_common::llm_deepinfra::{cheap_prompt, strip_think};
use non_empty_string::NonEmptyString;
use serde::Serialize;

use crate::types::processed::OrgName;

pub async fn org_split_from_dump(org_dump: &str) -> anyhow::Result<Vec<String>> {
    let prompt = format!(
        r#"We have an unformatted list of individuals and or organizations, try and parse them out as a json serializable list of organizations like so, we are also trying to match the organizations on their name, so removing the d/b/a suffix is important. YOUR RESPONSE MUST BE JSON SERIALIZABLE AND CONTAIN NO OTHER TEXT:
Example 1:
Manhattan Telecommunications Corporation LLC d/b/a Metropolitan Communications Solutions, LLC
Response 1:
["Manhattan Telecommunications Corporation LLC"]

Example 2:
Dunkirk and Fredonia Telephone Company, Niagara Mohawk Energy Marketing
Response 2:
["Dunkirk and Fredonia Telephone Company", "Niagara Mohawk Energy Marketing"]

Example 3:
Broadview Networks, Inc., CTC Communications Corp., Conversent Communications of New York, LLC, Eureka Telecom, Inc., PAETEC Communications, LLC, US LEC Communications, Inc.
Response 3:
["Broadview Networks, Inc","CTC Communications Corp", "Conversent Communications of New York, LLC", "Eureka Telecom, Inc", "PAETEC Communications, LLC","US LEC Communications, Inc"]

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

pub async fn split_and_fix_author_blob(auth_blob: &str) -> Vec<OrgName> {
    if auth_blob.is_empty() {
        return Vec::new();
    }
    let Ok(llm_parsed_names) = org_split_from_dump(auth_blob).await else {
        return clean_organization_name(auth_blob.to_string())
            .as_slice()
            .to_owned();
    };
    tracing::info!(previous_name=%auth_blob, new_list =?llm_parsed_names,"Parsed list into a bunch of llm names.");
    clean_up_author_list(llm_parsed_names)
}

pub fn clean_up_author_list(raw_llmed_list: Vec<String>) -> Vec<OrgName> {
    raw_llmed_list
        .into_iter()
        .filter_map(clean_organization_name)
        .collect()
}

// The suffix should be a standardized lowercase string like ["llc", "co", "corp", "inc", "company", "ltd", "lp", "llp"]
fn clean_organization_name(name: String) -> Option<OrgName> {
    let mut cleaned = name.trim().to_string();

    // Remove d/b/a patterns and everything after
    if let Some(dba_pos) = cleaned.to_lowercase().find(" d/b/a ") {
        cleaned = cleaned[..dba_pos].trim().to_string();
    }

    // Canonical suffixes (case insensitive matching → canonical lowercase form)
    let suffixes_to_remove: Vec<(&str, &str)> = vec![
        (" LLC", "llc"),
        (" L.L.C", "llc"),
        (" Inc", "inc"),
        (" Incorporated", "inc"),
        (" Corp", "corp"),
        (" Corporation", "corp"),
        (" Co", "co"),
        (" Company", "company"),
        (" Ltd", "ltd"),
        (" Limited", "ltd"),
        (" LP", "lp"),
        (" L.P", "lp"),
        (" LLP", "llp"),
        (" L.L.P", "llp"),
    ];
    let trim_punctuation = &['\'', '.', ',', ' '];

    let mut found_suffix: Option<String> = None;

    // Remove suffixes (case insensitive)
    for (suffix, canonical) in &suffixes_to_remove {
        if cleaned.to_lowercase().ends_with(&suffix.to_lowercase()) {
            let new_len = cleaned.len() - suffix.len();
            cleaned = cleaned[..new_len].trim().to_string();
            found_suffix = Some((*canonical).to_string());
            break; // Only remove one suffix to avoid over-cleaning
        }
    }

    cleaned = cleaned.trim_matches(trim_punctuation).trim().to_string();

    // Ensure we have a nonempty name
    let nonempty_name = NonEmptyString::new(cleaned).ok()?;

    Some(OrgName {
        name: nonempty_name,
        suffix: found_suffix.unwrap_or_default(),
    })
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
