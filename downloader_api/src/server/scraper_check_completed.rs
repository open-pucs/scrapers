use aide::axum::IntoApiResponse;
use axum::{Json, extract::Path};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{
    server::s3_routes::JurisdictionPath,
    types::{
        deduplication::DoubleDeduplicated, env_vars::OPENSCRAPERS_S3,
        openscraper_types::JurisdictionInfo,
    },
};

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
struct JuristdictionCaselistBreakdown {
    to_process: Vec<Value>,
    missing_completed: Vec<Value>,
    completed: Vec<Value>,
}

pub async fn get_completed_casedata_differential(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
    Json(caselist): Json<Vec<Value>>,
) -> impl IntoApiResponse {
    type ValueIdList = Vec<(String, Value)>;
    let user_caselist_values = caselist
        .into_iter()
        .filter_map(|value| {
            let govid = value.get("docket_govid").and_then(|v| v.as_str())?;
            Some((govid.to_string(), value))
        })
        .collect::<Vec<_>>();
    let s3_client = OPENSCRAPERS_S3.make_s3_client().await;
    let country = "usa".to_string(); // Or get from somewhere else
    let jur_info = JurisdictionInfo {
        state,
        country,
        jurisdiction: jurisdiction_name,
    };
    let result = crate::s3_stuff::list_cases_for_jurisdiction(&s3_client, &jur_info).await;
    let s3_caselist = match result {
        Ok(val) => val,
        Err(err) => return Err(err.to_string()),
    };
    let s3_valuelist: ValueIdList = s3_caselist
        .into_iter()
        .map(|id| (id.clone(), id.into()))
        .collect();
    let deduped =
        DoubleDeduplicated::make_double_deduplicated_with_keys(user_caselist_values, s3_valuelist);

    let return_val = JuristdictionCaselistBreakdown {
        to_process: deduped.in_base,
        missing_completed: deduped.in_comparison,
        completed: deduped.in_both,
    };
    Ok(Json(return_val))
}
