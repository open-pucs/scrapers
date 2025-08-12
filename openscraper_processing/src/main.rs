#![allow(dead_code)]
use common::{
    api_documentation::generate_api_docs_and_serve,
    misc::internet_check::do_i_have_internet,
    otel_tracing::initialize_tracing_and_wrap_router,
    tasks::{routing::define_generic_task_routes, workers::spawn_worker_loop},
};
use tracing::info;

use crate::server::define_routes;

use axum::extract::DefaultBodyLimit;

use std::{
    net::{Ipv4Addr, SocketAddr},
    sync::LazyLock,
};

mod case_worker;
mod common;
mod processing;
mod s3_stuff;
mod server;
mod types;
// use opentelemetry::global::{self, BoxedTracer, ObjectSafeTracerProvider, tracer};

// Note that this clones the document on each request.
// To be more efficient, we could wrap it into an Arc,
// or even store it as a serialized string.

const DEFAULT_PORT: u16 = 33399;
static PORT: LazyLock<u16> = LazyLock::new(|| {
    std::env::var("PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_PORT)
});

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    if let Err(e) = do_i_have_internet() {
        tracing::error!(err = %e,"NO INTERNET DETECTED");
        panic!("NO INTERNET DETECTED");
    }
    // initialise our subscriber
    let make_api = || {
        let routes = define_routes();
        let app = define_generic_task_routes(routes);
        app.layer(DefaultBodyLimit::disable())
    };
    let app = initialize_tracing_and_wrap_router(make_api)?;

    // Spawn background worker to process PDF tasks
    // This worker runs indefinitely
    info!("App Created, spawning background process:");

    // Spawns the background processing loop
    spawn_worker_loop();

    // bind and serve
    let addr = SocketAddr::new(Ipv4Addr::UNSPECIFIED.into(), *PORT);
    info!(?addr, "Starting application on adress");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    let app_description = "A component of the openscrapers library designed to efficently and cheaply process goverment docs at scale.";
    let Err(serve_error) = generate_api_docs_and_serve(listener, app, app_description).await;
    tracing::error!(
        %serve_error,
        "Encountered error while serving applicaiton, exiting immediately."
    );

    Ok(())
}
