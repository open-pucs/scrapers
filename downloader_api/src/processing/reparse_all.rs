use std::time::Duration;

use async_trait::async_trait;
use aws_sdk_s3::Client;
use axum::{Json, extract::Path};
use futures_util::{StreamExt, stream};
use mycorrhiza_common::{
    s3_generic::fetchers_and_getters::S3Addr,
    tasks::{
        ExecuteUserTask, TaskStatusDisplay, workers::add_task_to_queue_and_wait_to_see_if_done,
    },
};

use crate::{
    s3_stuff::{
        fetch_case_filing_from_s3, get_case_s3_key, list_cases_for_jurisdiction, push_case_to_s3,
    },
    server::s3_routes::JurisdictionPath,
    types::{
        data_processing_traits::{ReParse, Revalidate},
        env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET},
        jurisdictions::JurisdictionInfo,
    },
};

pub struct ReparseCleanJurisdiction(pub JurisdictionInfo);

#[async_trait]
impl ExecuteUserTask for ReparseCleanJurisdiction {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let res = reparse_clean_jurisdiction(self.0).await;
        match res {
            Ok(()) => Ok("Successfully reparsed all files in jurisdiction.".into()),
            Err(e) => Err(e.to_string().into()),
        }
    }
    fn get_task_label_static() -> &'static str
    where
        Self: Sized,
    {
        "reparse_clean_jurisdiction"
    }
    fn get_task_label(&self) -> &'static str {
        "reparse_clean_jurisdiction"
    }
}

pub async fn reparse_clean_jurisdiction_handler(
    Path(JurisdictionPath {
        state,
        jurisdiction_name,
    }): Path<JurisdictionPath>,
) -> Json<TaskStatusDisplay> {
    let country = "usa".to_string();
    let jur_info = JurisdictionInfo {
        state,
        country,
        jurisdiction: jurisdiction_name,
    };
    let obj = ReparseCleanJurisdiction(jur_info);
    let wait_dur = Duration::from_secs(1);
    let display_return = add_task_to_queue_and_wait_to_see_if_done(obj, 0, wait_dur)
        .await
        .into();
    Json(display_return)
}

async fn reparse_clean_jurisdiction(jur_info: JurisdictionInfo) -> anyhow::Result<()> {
    let s3_client = OPENSCRAPERS_S3.make_s3_client().await;
    let docketlist = list_cases_for_jurisdiction(&s3_client, &jur_info).await?;
    let docket_closure = async |docket_govid: &String| {
        let _ = reparse_clean_docket(&s3_client, docket_govid, &jur_info).await;
    };
    let docket_futures = docketlist.iter().map(docket_closure);
    let _ = stream::iter(docket_futures)
        .buffer_unordered(30)
        .count()
        .await;

    Ok(())
}

async fn reparse_clean_docket(
    s3_client: &Client,
    docket_govid: &str,
    jur_info: &JurisdictionInfo,
) -> anyhow::Result<()> {
    let Ok(mut docket) = fetch_case_filing_from_s3(s3_client, docket_govid, jur_info).await else {
        // Clean docket if fetch failed.
        let docket_key = get_case_s3_key(docket_govid, jur_info);
        tracing::warn!(%docket_govid, %docket_key,"Could not properly serialize docket, deleting out of an abundance of caution.");
        S3Addr::new(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &docket_key)
            .delete_file()
            .await?;
        return Ok(());
    };
    docket.revalidate();
    let Ok(_) = docket.re_parse().await;
    push_case_to_s3(s3_client, &docket, jur_info).await?;
    Ok(())
}
