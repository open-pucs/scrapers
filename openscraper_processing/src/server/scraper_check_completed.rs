use aide::axum::IntoApiResponse;
use axum::{Json, body::Body, extract::Path};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::{
    server::s3_routes::JurisdictionPath,
    types::{deduplication::DoubleDeduplicated, env_vars::OPENSCRAPERS_S3},
};

#[derive(Clone, Serialize, Deserialize, JsonSchema)]
struct JuristdictionCaselistBreakdown {
    to_process: Vec<String>,
    missing_completed: Vec<String>,
    completed: Vec<String>,
}

pub async fn get_completed_cases_differential(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
    Json(caselist): Json<Vec<String>>,
    // ) -> Result<Json<JuristdictionCaselistBreakdown>, String> {
) -> impl IntoApiResponse {
    let s3_client = OPENSCRAPERS_S3.make_s3_client().await;
    let country = "usa"; // Or get from somewhere else
    let result = crate::s3_stuff::list_cases_for_jurisdiction(
        &s3_client,
        &jurisdiction_name,
        &state,
        country,
    )
    .await;
    let s3_caselist = match result {
        Ok(val) => val,
        Err(err) => return Err(err.to_string()),
    };
    let deduped = DoubleDeduplicated::make_double_deduplicated(caselist, s3_caselist);

    let return_val = JuristdictionCaselistBreakdown {
        to_process: deduped.in_base,
        missing_completed: deduped.in_comparison,
        completed: deduped.in_both,
    };
    Ok(Json(return_val))
}
