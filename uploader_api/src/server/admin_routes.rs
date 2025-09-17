use aide::axum::{
    ApiRouter,
    routing::{delete, post},
};

use crate::server::queue_routes::{self, submit_cases_to_queue_without_download};
use crate::server::s3_routes;
use crate::server::temporary_routes::define_temporary_routes;

pub fn create_admin_router() -> ApiRouter {
    let admin_routes = ApiRouter::new()
        .api_route(
            "/cases/upload_raw",
            post(submit_cases_to_queue_without_download),
        )
        .api_route("/write_s3_string", post(s3_routes::write_s3_file_string))
        .api_route("/write_s3_json", post(s3_routes::write_s3_file_json))
        .api_route(
            "/cases/{state}/{jurisdiction_name}/purge_all",
            delete(s3_routes::recursive_delete_all_jurisdiction_data),
        );

    // Temporary routes are also admin routes
    define_temporary_routes(admin_routes)
}
