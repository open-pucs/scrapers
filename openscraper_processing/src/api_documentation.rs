use tokio::net::TcpListener;
use tracing::info;

use aide::{
    axum::{ApiRouter, IntoApiResponse},
    openapi::{Info, OpenApi},
};
use axum::response::IntoResponse;

use std::sync::OnceLock;

use aide::{axum::routing::get, swagger::Swagger};
static PRESERIALIZED_API_STRING: OnceLock<String> = OnceLock::new();
pub async fn serve_api() -> impl IntoApiResponse {
    // First, check if we have a cached serialized version
    if let Some(cached_json) = PRESERIALIZED_API_STRING.get() {
        let static_json: &'static str = cached_json;
        return static_json.into_response();
    }
    (
        axum::http::StatusCode::INTERNAL_SERVER_ERROR,
        "The API doesnt exist, this should have caused the listener to never start, seems weird.",
    )
        .into_response()
}

pub async fn generate_api_docs_and_serve(
    listener: TcpListener,
    app: ApiRouter,
    app_description: &str,
) -> Result<(), std::io::Error> {
    let mut api = OpenApi {
        info: Info {
            description: Some(app_description.to_string()),
            ..Info::default()
        },
        ..OpenApi::default()
    };
    info!("Initialized OpenAPI");
    let full_service = app
        .route("/api.json", get(serve_api))
        .route("/swagger", Swagger::new("/api.json").axum_route())
        // Generate the documentation.
        .finish_api(&mut api)
        .into_make_service();

    // No cached version exists, so we need to serialize and cache it
    match serde_json::to_string(&api) {
        Ok(serialized) => {
            // Successfully serialized, now cache it
            PRESERIALIZED_API_STRING.get_or_init(|| serialized);
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
            tracing::error!("{error_response}");
            panic!("{error_response}");
        }
    }
    axum::serve(listener, full_service).await
}
