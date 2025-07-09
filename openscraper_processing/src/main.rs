use tracing::info;

use crate::{server::define_routes, worker::start_workers};

use aide::{
    axum::{ApiRouter, IntoApiResponse, routing::get},
    openapi::{Info, OpenApi},
    swagger::Swagger,
};
use axum::{Extension, Json};

use std::net::{Ipv4Addr, SocketAddr};

mod s3_stuff;
mod server;
mod types;
mod worker;
// use opentelemetry::global::{self, BoxedTracer, ObjectSafeTracerProvider, tracer};

// Note that this clones the document on each request.
// To be more efficient, we could wrap it into an Arc,
// or even store it as a serialized string.
async fn serve_api(Extension(api): Extension<OpenApi>) -> impl IntoApiResponse {
    Json(api)
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    info!("Tracing Subscriber is up and running, trying to create app");
    // initialise our subscriber
    let routes = define_routes();
    let app = routes
        .api_route("/health", get(health))
        .route("/api.json", get(serve_api))
        .route("/swagger", Swagger::new("/api.json").axum_route());

    // Spawn background worker to process PDF tasks
    // This worker runs indefinitely
    info!("App Created, spawning background process:");
    tokio::spawn(async move {
        start_workers().await;
    });

    // bind and serve
    let addr = SocketAddr::new(Ipv4Addr::new(0, 0, 0, 0).into(), 8000);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    info!("Listening on http://{}", addr);
    let mut api = OpenApi {
        info: Info {
            description: Some("A component of the openscrapers library designed to efficently and cheaply process goverment docs at scale.".to_string()),
            ..Info::default()
        },
        ..OpenApi::default()
    };
    info!("Initialized OpenAPI");
    axum::serve(
        listener,
        app
            // Generate the documentation.
            .finish_api(&mut api)
            // Expose the documentation to the handlers.
            .layer(Extension(api))
            .into_make_service(),
    )
    .await
    .unwrap();
    // });

    Ok(())
}

/// Get health of the API.
async fn health() -> &'static str {
    "Service is Healthy"
}
