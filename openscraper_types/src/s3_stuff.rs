use mycorrhiza_common::s3_generic::S3Credentials;
use mycorrhiza_common::s3_generic::cannonical_location::CannonicalS3ObjectLocation;

use crate::env_vars::{OPENSCRAPERS_S3, OPENSCRAPERS_S3_OBJECT_BUCKET};
use crate::jurisdictions::JurisdictionInfo;
use crate::raw::RawGenericDocket;

pub struct DocketAddress {
    pub docket_govid: String,
    pub jurisdiction: JurisdictionInfo,
}

impl CannonicalS3ObjectLocation for RawGenericDocket {
    type AddressInfo = DocketAddress;

    fn generate_object_key(addr: &Self::AddressInfo) -> String {
        let country = &*addr.jurisdiction.country;
        let state = &*addr.jurisdiction.state;
        let jurisdiction = &*addr.jurisdiction.jurisdiction;
        let case_name = &*addr.docket_govid;
        format!("objects_raw/{country}/{state}/{jurisdiction}/{case_name}")
    }
    fn generate_bucket(_: &Self::AddressInfo) -> &'static str {
        &OPENSCRAPERS_S3_OBJECT_BUCKET
    }
    fn get_credentials(_: &Self::AddressInfo) -> &'static S3Credentials {
        &OPENSCRAPERS_S3
    }
}
