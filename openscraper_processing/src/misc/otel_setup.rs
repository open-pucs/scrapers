use init_tracing_opentelemetry::{
    init_propagator, //stdio,
    otlp,
    resource::DetectResource,
    tracing_subscriber_ext::build_logger_text,
};
use opentelemetry::trace::TracerProvider;
use opentelemetry_sdk::trace::{SdkTracerProvider, Tracer};
use tracing::{Subscriber, info};
use tracing_opentelemetry::OpenTelemetryLayer;
use tracing_subscriber::{filter::EnvFilter, layer::SubscriberExt, registry::LookupSpan};

pub fn build_loglevel_filter_layer() -> tracing_subscriber::filter::EnvFilter {
    // TLDR: Unsafe because its not thread safe, however we arent using it in that context so
    // everything should be fine: https://doc.rust-lang.org/std/env/fn.set_var.html#safety
    unsafe {
        std::env::set_var(
            "RUST_LOG",
            format!(
                "{},otel::tracing=trace,otel=debug",
                std::env::var("OTEL_LOG_LEVEL").unwrap_or_else(|_| "info".to_string())
            ),
        );
    }
    EnvFilter::from_default_env()
}

pub fn build_otel_layer<S>() -> anyhow::Result<(OpenTelemetryLayer<S, Tracer>, SdkTracerProvider)>
where
    S: Subscriber + for<'a> LookupSpan<'a>,
{
    use opentelemetry::global;
    let otel_rsrc = DetectResource::default()
        .with_fallback_service_name(env!("CARGO_PKG_NAME"))
        .build();
    let tracer_provider = otlp::init_tracerprovider(otel_rsrc, otlp::identity)?;

    init_propagator()?;
    let layer = tracing_opentelemetry::layer()
        .with_error_records_to_exceptions(true)
        .with_tracer(tracer_provider.tracer(""));
    global::set_tracer_provider(tracer_provider.clone());
    Ok((layer, tracer_provider))
}

pub fn init_subscribers_and_loglevel() -> anyhow::Result<SdkTracerProvider> {
    //setup a temporary subscriber to log output during setup
    let subscriber = tracing_subscriber::registry()
        .with(build_loglevel_filter_layer())
        .with(build_logger_text());
    let _guard = tracing::subscriber::set_default(subscriber);
    info!("init logging & tracing");

    let (layer, guard) = build_otel_layer()?;

    let subscriber = tracing_subscriber::registry()
        .with(layer)
        .with(build_loglevel_filter_layer())
        .with(build_logger_text());
    tracing::subscriber::set_global_default(subscriber)?;
    Ok(guard)
}
