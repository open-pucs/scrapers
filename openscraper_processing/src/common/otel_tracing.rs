use aide::axum::ApiRouter;
use axum_tracing_opentelemetry::middleware::{OtelAxumLayer, OtelInResponseLayer};
use init_tracing_opentelemetry::tracing_subscriber_ext::init_subscribers_and_loglevel;
use tracing::info;

pub fn initialize_tracing_and_wrap_router(
    make_api: impl FnOnce() -> ApiRouter,
) -> anyhow::Result<ApiRouter> {
    let _ = init_subscribers_and_loglevel("")?;

    info!("Tracing Subscriber is up and running, trying to create app");
    let api_router = make_api()
        .layer(OtelInResponseLayer)
        //start OpenTelemetry trace on incoming request
        .layer(OtelAxumLayer::default());

    Ok(api_router)
}
