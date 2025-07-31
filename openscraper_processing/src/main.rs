#![allow(dead_code)]
use axum_tracing_opentelemetry::middleware::{OtelAxumLayer, OtelInResponseLayer};
use misc::{internet_check::do_i_have_internet, otel_setup::init_subscribers_and_loglevel};
use tracing::{Instrument, info};

use crate::{server::define_routes, worker::start_workers};

use axum::extract::DefaultBodyLimit;

use std::net::{Ipv4Addr, SocketAddr};

mod api_documentation;
mod misc;
mod processing;
mod s3_stuff;
mod server;
mod types;
mod worker;
// use opentelemetry::global::{self, BoxedTracer, ObjectSafeTracerProvider, tracer};

// Note that this clones the document on each request.
// To be more efficient, we could wrap it into an Arc,
// or even store it as a serialized string.

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ =
        init_subscribers_and_loglevel().expect("Failed to initialize opentelemetry tracing stuff");
    if let Err(e) = do_i_have_internet() {
        tracing::error!(err = %e,"NO INTERNET DETECTED");
        panic!("NO INTERNET DETECTED");
    }
    // initialise our subscriber
    let routes = define_routes();
    let app = routes
        .layer(OtelInResponseLayer)
        //start OpenTelemetry trace on incoming request
        .layer(OtelAxumLayer::default())
        .layer(DefaultBodyLimit::disable());

    // Spawn background worker to process PDF tasks
    // This worker runs indefinitely
    info!("App Created, spawning background process:");
    tokio::spawn(
        async move {
            info!("Attempting to diagnose trace inside a tokio spawn?");

            let result = start_workers().await;
            let Err(err) = result;
            tracing::error!(%err,"Encountered error while running the workers. The worker has stopped.");
            println!("Encountered error while running the workers. The worker has stopped: {err}");
            eprintln!("Encountered error while running the workers. The worker has stopped: {err}");
        }
        .in_current_span(),
    );

    // bind and serve
    let addr = SocketAddr::new(Ipv4Addr::UNSPECIFIED.into(), 8000);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    let app_description = "A component of the openscrapers library designed to efficently and cheaply process goverment docs at scale.";
    api_documentation::generate_api_docs_and_serve(listener, app, app_description).await?;
    info!("Listening on http://{}", addr);

    Ok(())
}
