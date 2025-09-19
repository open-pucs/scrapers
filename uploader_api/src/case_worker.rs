use crate::s3_stuff::make_s3_client;
use anyhow::anyhow;
use async_trait::async_trait;
use aws_sdk_s3::Client;
use chrono::Utc;
use mycorrhiza_common::s3_generic::cannonical_location::{
    download_openscrapers_object, upload_object,
};
use mycorrhiza_common::tasks::ExecuteUserTask;
use openscraper_types::jurisdictions::JurisdictionInfo;
use openscraper_types::raw::RawGenericDocket;
use openscraper_types::s3_stuff::DocketAddress;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Deserialize, Serialize, JsonSchema)]
pub struct RawDocketIngestInfo {
    pub docket: RawGenericDocket,
    pub jurisdiction: JurisdictionInfo,
    #[serde(default)]
    pub upload_type: RawDocketUploadType,
}

#[repr(transparent)]
pub struct ProcessCaseWithoutDownload(pub RawDocketIngestInfo);

#[derive(Clone, Default, Copy, Deserialize, Serialize, JsonSchema, Debug)]
#[serde(rename_all = "snake_case")]
pub enum RawDocketUploadType {
    #[default]
    All,
    OnlyFillings,
    OnlyParties,
    OnlyMetadata,
}

impl RawDocketUploadType {
    fn join_dockets(
        &self,
        mut uploaded: RawGenericDocket,
        mut original: RawGenericDocket,
    ) -> anyhow::Result<RawGenericDocket> {
        if uploaded.case_govid != original.case_govid {
            return Err(anyhow!(
                "Docket id's do not match for dockets that are being merged."
            ));
        }
        let mut modified_case = match self {
            RawDocketUploadType::All => uploaded,
            RawDocketUploadType::OnlyFillings => {
                original.filings = uploaded.filings;
                original
            }
            RawDocketUploadType::OnlyParties => {
                original.case_parties = uploaded.case_parties;
                original
            }
            RawDocketUploadType::OnlyMetadata => {
                uploaded.filings = original.filings;
                uploaded.case_parties = original.case_parties;
                uploaded
            }
        };
        modified_case.indexed_at = Utc::now();
        Ok(modified_case)
    }
    async fn download_and_compare(
        &self,
        s3_client: &Client,
        uploaded_docket: RawGenericDocket,
        docket_address: &DocketAddress,
    ) -> anyhow::Result<RawGenericDocket> {
        let original_docket =
            download_openscrapers_object::<RawGenericDocket>(s3_client, docket_address).await?;
        let final_docket = self.join_dockets(uploaded_docket, original_docket)?;
        Ok(final_docket)
    }
}
#[async_trait]
impl ExecuteUserTask for ProcessCaseWithoutDownload {
    async fn execute_task(self: Box<Self>) -> Result<serde_json::Value, serde_json::Value> {
        let res = upload_docket_with_info(self.0).await;
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

pub async fn upload_docket_with_info(ingest_info: RawDocketIngestInfo) -> anyhow::Result<()> {
    let s3_client = make_s3_client().await;
    let RawDocketIngestInfo {
        docket,
        jurisdiction,
        upload_type,
    } = ingest_info;
    let docket_address = DocketAddress {
        docket_govid: docket.case_govid.clone().to_string(),
        jurisdiction,
    };
    let joined_docket_result = upload_type
        .download_and_compare(&s3_client, docket, &docket_address)
        .await;
    let joined_docket = match joined_docket_result {
        Ok(val) => val,
        Err(e) => return Err(e),
    };
    upload_object::<RawGenericDocket>(&s3_client, &docket_address, &joined_docket)
        .await
        .map_err(|err| err)
}
