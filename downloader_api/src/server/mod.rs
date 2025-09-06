use aide::axum::ApiRouter;
use mycorrhiza_common::misc::is_env_var_true;
use std::sync::LazyLock;
use tracing::info;

pub mod queue_routes;
pub mod s3_routes;
pub mod scraper_check_completed;
pub mod temporary_routes;

pub mod admin_routes;
pub mod health_routes;
pub mod public_routes;

static PUBLIC_SAFE_MODE: LazyLock<bool> = LazyLock::new(|| is_env_var_true("PUBLIC_SAFE_MODE"));

pub fn define_routes() -> ApiRouter {
    let public_routes = public_routes::create_public_router();
    let health_routes = health_routes::create_health_and_test_router();

    let mut app = ApiRouter::new()
        .merge(health_routes)
        .nest("/public", public_routes);

    if !*PUBLIC_SAFE_MODE {
        info!("Public safe mode disabled, admin routes are enabled.");
        let admin_routes = admin_routes::create_admin_router();
        app = app.nest("/admin", admin_routes);
    } else {
        info!("Public safe mode enabled, admin routes are disabled.");
    }

    info!("Routes defined successfully");
    app
}
