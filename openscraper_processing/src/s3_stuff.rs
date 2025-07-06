use aws_config::{BehaviorVersion, Region};
use aws_sdk_s3::{Client, config::Credentials};

use crate::types::env_vars::{
    OPENSCRAPERS_S3_ACCESS_KEY, OPENSCRAPERS_S3_CLOUD_REGION, OPENSCRAPERS_S3_ENDPOINT,
    OPENSCRAPERS_S3_SECRET_KEY,
};

pub async fn make_s3_client() -> Client {
    let region = Region::new(&*OPENSCRAPERS_S3_CLOUD_REGION);
    let creds = Credentials::new(
        &*OPENSCRAPERS_S3_ACCESS_KEY,
        &*OPENSCRAPERS_S3_SECRET_KEY,
        None, // no session token
        None, // no expiration
        "manual",
    );

    // Start from the env-loader so we still pick up other settings (timeouts, retry, etc)
    let cfg_loader = aws_config::defaults(BehaviorVersion::latest())
        .region(region)
        .credentials_provider(creds)
        .endpoint_url(&*OPENSCRAPERS_S3_ENDPOINT);

    let sdk_config = cfg_loader.load().await;
    Client::new(&sdk_config)
}
