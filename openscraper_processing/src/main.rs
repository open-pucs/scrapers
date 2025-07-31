#![allow(dead_code)]
use axum_tracing_opentelemetry::middleware::{OtelAxumLayer, OtelInResponseLayer};
use misc::{internet_check::do_i_have_internet, otel_setup::init_subscribers_and_loglevel};
use tracing::{Instrument, info};

use crate::{server::define_routes, worker::start_workers};

use aide::{
    axum::{IntoApiResponse, routing::get},
    openapi::{Info, OpenApi},
    swagger::Swagger,
};
use axum::{Extension, Json, extract::DefaultBodyLimit, response::IntoResponse};

use std::{
    net::{Ipv4Addr, SocketAddr},
    sync::{LazyLock, OnceLock},
};

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
static PRESERIALIZED_API_STRING: OnceLock<String> = OnceLock::new();
async fn serve_api(Extension(api): Extension<OpenApi>) -> impl IntoApiResponse {
    // First, check if we have a cached serialized version
    if let Some(cached_json) = PRESERIALIZED_API_STRING.get() {
        return cached_json.clone().into_response();
    }

    // No cached version exists, so we need to serialize and cache it
    match serde_json::to_string(&api) {
        Ok(serialized) => {
            // Successfully serialized, now cache it
            let returned_val = PRESERIALIZED_API_STRING.get_or_init(|| serialized);

            // Return the serialized JSON string
            returned_val.clone().into_response()
        }
        Err(e) => {
            // Serialization failed - return detailed error information
            let error_response = format!(
                "Failed to serialize OpenAPI specification: {}\n\
                Error type: {}\n\
                This typically occurs when:\n\
                - The OpenAPI struct contains non-serializable fields\n\
                - There are circular references in the data structure\n\
                - Custom types don't implement Serialize properly\n\
                - There are invalid UTF-8 sequences in string fields
                Debug Object:\n{:?}",
                e,
                std::any::type_name_of_val(&e),
                &api
            );

            // Return error as plain text response with appropriate status
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                [("content-type", "text/plain")],
                error_response,
            )
                .into_response()
        }
    }
}

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
        .route("/api.json", get(serve_api))
        .route("/swagger", Swagger::new("/api.json").axum_route())
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
