use tracing::info;

use crate::worker::start_workers;

mod s3_stuff;
mod server;
mod types;
mod worker;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    info!("Starting workers");
    start_workers().await?;
    Ok(())
}
