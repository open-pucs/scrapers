use std::time::Duration;
#[derive(Debug, thiserror::Error)]
#[error("No internet connection available")]
pub struct NoInternetError {}

const CONNECTION_ADDRESS: &str = "google.com:80";
const TIMEOUT_SECONDS: u64 = 5;

pub fn do_i_have_internet() -> Result<(), NoInternetError> {
    use std::net::{TcpStream, ToSocketAddrs};
    let addresses = CONNECTION_ADDRESS
        .to_socket_addrs()
        .map_err(|_| NoInternetError {})?;

    for addr in addresses {
        if TcpStream::connect_timeout(&addr, Duration::from_secs(TIMEOUT_SECONDS)).is_ok() {
            return Ok(());
        }
    }

    Err(NoInternetError {})
}

pub async fn do_i_have_internet_async() -> Result<(), NoInternetError> {
    use reqwest::{Client, Url};
    use tracing::error;

    let client = Client::builder()
        .timeout(Duration::from_secs(TIMEOUT_SECONDS))
        .build()
        .map_err(|err| {
            error!(%err,"Could not build internet client.");
            NoInternetError {}
        })?;

    match client
        .get("https://www.google.com/generate_204")
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => Ok(()),
        Ok(resp) => {
            error!(status = %resp.status(), "Non-success response");
            Err(NoInternetError {})
        }
        Err(err) => {
            error!(%err, "Request failed");
            Err(NoInternetError {})
        }
    }
}
