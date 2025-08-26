use axum::Json;
use chrono::{DateTime, Utc};
use futures_util::{StreamExt, stream};
use mycorrhiza_common::tasks::ExecuteUserTask;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::{
    processing::ReprocessDocketInfo,
    s3_stuff::{
        DocketAddress, download_openscrapers_object, list_processed_cases_for_jurisdiction,
        make_s3_client, upload_object,
    },
    types::{
        data_processing_traits::DownloadIncomplete, jurisdictions::JurisdictionInfo,
        processed::ProcessedGenericDocket,
    },
};

const fn default_true() -> bool {
    true
}

#[derive(Serialize, Deserialize, JsonSchema)]
pub struct ReprocessJurisdictionInfo {
    pub jurisdiction: JurisdictionInfo,
    pub ignore_cached_older_than: Option<DateTime<Utc>>,
    #[serde(default = "default_true")]
    pub only_process_missing: bool,
}

pub async fn reprocess_dockets(
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
        .buffer_unordered(10)
        .collect::<Vec<_>>()
        .await;

    Ok("Successfully added processing tasks to queue".to_string())
}

pub async fn download_all_missing_hashes(
    Json(payload): Json<JurisdictionInfo>,
) -> Result<String, String> {
    let s3_client = make_s3_client().await;
    let processed_caselist = list_processed_cases_for_jurisdiction(&s3_client, &payload)
        .await
        .map_err(|e| e.to_string())?;
    let extra_info = (s3_client.clone(), payload.clone());
    let _tasks = stream::iter(processed_caselist.into_iter())
        .map(|docket_govid| async {
            let docket_address = DocketAddress {
                jurisdiction: payload.clone(),
                docket_govid,
            };
            if let Ok(mut proc_docket) =
                download_openscrapers_object::<ProcessedGenericDocket>(&s3_client, &docket_address)
                    .await
            {
                let res = proc_docket.download_incomplete(&extra_info).await;
                if res.is_ok() {
                    let _ = upload_object(&s3_client, &docket_address, &proc_docket).await;
                }
            };
        })
        .buffer_unordered(4)
        .collect::<Vec<_>>()
        .await;
    Ok("Completed Successfully".into())
}
