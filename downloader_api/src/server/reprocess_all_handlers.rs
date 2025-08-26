use axum::Json;
use chrono::{DateTime, Utc};
use futures_util::{StreamExt, stream};
use mycorrhiza_common::tasks::ExecuteUserTask;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::{
    processing::ReprocessDocketInfo,
    s3_stuff::{list_processed_cases_for_jurisdiction, make_s3_client},
    types::jurisdictions::JurisdictionInfo,
};

const fn default_true() -> bool {
    true
}

#[derive(Serialize, Deserialize, JsonSchema)]
struct ReprocessJurisdictionInfo {
    jurisdiction: JurisdictionInfo,
    ignore_cached_older_than: Option<DateTime<Utc>>,
    #[serde(default = "default_true")]
    only_process_missing: bool,
}

async fn reprocess_dockets(
    Json(payload): Json<ReprocessJurisdictionInfo>,
) -> Result<String, String> {
    let s3_client = make_s3_client().await;
    let processed_caselist =
        list_processed_cases_for_jurisdiction(&s3_client, &payload.jurisdiction)
            .await
            .map_err(|e| e.to_string())?;
    let boxed_tasks = processed_caselist.into_iter().map(|docket_govid| {
        let task_info = ReprocessDocketInfo {
            docket_govid,
            jurisdiction: payload.jurisdiction.clone(),
            only_process_missing: payload.only_process_missing,
            ignore_cachced_if_older_than: payload.ignore_cached_older_than,
        };
        Box::new(task_info)
    });
    let _results = stream::iter(boxed_tasks)
        .map(ExecuteUserTask::execute_task)
        .buffer_unordered(3)
        .collect::<Vec<_>>()
        .await;

    Ok("Successfully added processing tasks to queue".to_string())
}
