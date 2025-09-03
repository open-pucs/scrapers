use crate::s3_stuff::make_s3_client;
use crate::types::raw::RawDocketWithJurisdiction;
use async_trait::async_trait;
use dokito_types::s3_stuff::DocketAddress;
use mycorrhiza_common::s3_generic::cannonical_location::upload_object;
use mycorrhiza_common::tasks::ExecuteUserTask;

#[repr(transparent)]
pub struct ProcessCaseWithoutDownload(pub RawDocketWithJurisdiction);

#[async_trait]
impl ExecuteUserTask for ProcessCaseWithoutDownload {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let s3_client = make_s3_client().await;
        let RawDocketWithJurisdiction {
            docket,
            jurisdiction,
        } = self.0;
        let docket_address = DocketAddress {
            docket_govid: docket.case_govid.clone().to_string(),
            jurisdiction: jurisdiction,
        };
        let res = upload_object(&s3_client, &docket_address, &docket).await;

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
