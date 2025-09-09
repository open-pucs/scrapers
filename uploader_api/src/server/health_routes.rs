
use aide::axum::{routing::get, ApiRouter};
use mycorrhiza_common::llm_deepinfra::test_deepinfra;

async fn return_healthy() -> &'static str {
    "service is healthy"
}

pub fn create_health_and_test_router() -> ApiRouter {
    ApiRouter::new()
        .api_route("/", get(return_healthy))
        .api_route("/health", get(return_healthy))
        .api_route("/test/deepinfra", get(test_deepinfra))
}
