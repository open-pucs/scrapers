use std::env;

use aide::axum::ApiRouter;
use axum_tracing_opentelemetry::middleware::{OtelAxumLayer, OtelInResponseLayer};
use init_tracing_opentelemetry::{
    otlp::OtelGuard, tracing_subscriber_ext::init_subscribers_and_loglevel,
};
use tracing::info;

pub fn initialize_tracing_and_wrap_router(
    make_api: impl FnOnce() -> ApiRouter,
) -> anyhow::Result<(ApiRouter, OtelGuard)> {
    if env::var("OTEL_SERVICE_NAME").is_err() {
        // a) Crate name – compile‑time constant, always available.
        let crate_name = env!("CARGO_PKG_NAME");

        // c) Host name – use the `hostname` crate.
        //    If it fails for any reason we fall back to "unknown".
        let host = hostname::get()
            .ok()
            .and_then(|os_str| os_str.into_string().ok())
            .unwrap_or_else(|| "unknown".to_string());

        // d) Assemble the final string.
        let generated = format!("{crate_name}-{host}");
        println!("OTEL_SERVICE_NAME was not set, defaulting to {generated}");

        // this is only used in a single threaded context upon initialization, so its fine.
        unsafe {
            env::set_var("OTEL_SERVICE_NAME", &generated);
        }
    }
    let tracing_guard = init_subscribers_and_loglevel("")?;

    info!("Tracing Subscriber is up and running, trying to create app");
    let api_router = make_api()
        .layer(OtelInResponseLayer)
        //start OpenTelemetry trace on incoming request
        .layer(OtelAxumLayer::default());

    Ok((api_router, tracing_guard))
}
