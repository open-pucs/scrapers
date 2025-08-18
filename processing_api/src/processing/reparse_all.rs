use async_trait::async_trait;
use aws_sdk_s3::Client;
use futures_util::{StreamExt, stream};

use crate::{
    common::tasks::ExecuteUserTask,
    s3_stuff::{
        delete_s3_file, fetch_case_filing_from_s3, get_case_s3_key, list_cases_for_jurisdiction,
        push_case_to_s3,
    },
    types::{
        data_processing_traits::{ReParse, Revalidate},
        env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET},
        openscraper_types::JurisdictionInfo,
    },
};

pub struct ReparseCleanJurisdiction(pub JurisdictionInfo);

// #[async_trait]
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

async fn reparse_clean_jurisdiction(jur_info: JurisdictionInfo) -> anyhow::Result<()> {
    let s3_client = OPENSCRAPERS_S3.make_s3_client().await;
    let docketlist = list_cases_for_jurisdiction(&s3_client, &jur_info).await?;
    let docket_futures = docketlist.iter().map(async |docket_govid| {
        let _ = reparse_clean_docket(&s3_client, docket_govid, &jur_info).await;
    });
    let _ = stream::iter(docket_futures)
        .buffer_unordered(5)
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
        delete_s3_file(s3_client, &OPENSCRAPERS_S3_OBJECT_BUCKET, &docket_key).await?;
        return Ok(());
    };
    docket.revalidate();
    let Ok(_) = docket.re_parse().await;
    push_case_to_s3(s3_client, &docket, jur_info).await?;
    Ok(())
}
