use crate::processing::process_case;
use crate::s3_stuff::make_s3_client;
use crate::types::raw::RawCaseWithJurisdiction;
use async_trait::async_trait;
use mycorrhiza_common::tasks::ExecuteUserTask;

#[repr(transparent)]
pub struct ProcessCaseWithDownload(pub RawCaseWithJurisdiction);

#[async_trait]
impl ExecuteUserTask for ProcessCaseWithDownload {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let s3_client = make_s3_client().await;
        let RawCaseWithJurisdiction { case, jurisdiction } = self.0;
        let extra_data = (s3_client, jurisdiction);
        let res = process_case(case, &extra_data, true).await;
        match res {
            Ok(()) => Ok("Task Completed Successfully".into()),
            Err(err) => Err(err.to_string().into()),
        }
    }
    fn get_task_label(&self) -> &'static str {
        "ingest_case_with_jurisdiction_and_download"
    }
    fn get_task_label_static() -> &'static str
    where
        Self: Sized,
    {
        "ingest_case_with_jurisdiction_and_download"
    }
}

#[repr(transparent)]
pub struct ProcessCaseWithoutDownload(pub RawCaseWithJurisdiction);

#[async_trait]
impl ExecuteUserTask for ProcessCaseWithoutDownload {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let s3_client = make_s3_client().await;
        let RawCaseWithJurisdiction { case, jurisdiction } = self.0;
        let extra_data = (s3_client, jurisdiction);
        todo!();
        let res = process_case(case, &extra_data, false).await;
        match res {
            Ok(()) => Ok("Task Completed Successfully".into()),
            Err(err) => Err(err.to_string().into()),
        }
    }
    fn get_task_label(&self) -> &'static str {
        "ingest_case_with_jurisdiction_and_download"
    }
    fn get_task_label_static() -> &'static str
    where
        Self: Sized,
    {
        "ingest_case_with_jurisdiction_and_download"
    }
}
