use crate::common::task_workers::ExecuteUserTask;
use crate::processing::process_case;
use crate::s3_stuff::make_s3_client;
use crate::types::CaseWithJurisdiction;
use async_trait::async_trait;

#[async_trait]
impl ExecuteUserTask for CaseWithJurisdiction {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let s3_client = make_s3_client().await;
        let res = process_case(&*self, &s3_client).await;
        match res {
            Ok(()) => Ok("Task Completed Successfully".into()),
            Err(err) => Err(err.to_string().into()),
        }
    }
    fn get_task_label(&self) -> &'static str {
        "ingest_case_with_jurisdiction"
    }
}
