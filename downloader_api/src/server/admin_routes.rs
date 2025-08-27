use aide::axum::{
    routing::{delete, post, post_with},
    ApiRouter,
};

use crate::server::direct_file_fetch::{
    handle_directly_process_file_request, handle_directly_process_file_request_docs,
};
use crate::server::queue_routes;
use crate::server::reprocess_all_handlers::{download_all_missing_hashes, reprocess_dockets};
use crate::server::s3_routes;
use crate::server::temporary_routes::define_temporary_routes;

pub fn create_admin_router() -> ApiRouter {
    let admin_routes = ApiRouter::new()
        .api_route(
            "/cases/submit",
            post_with(
                queue_routes::submit_case_to_queue_without_download,
                queue_routes::submit_case_to_queue_docs,
            ),
        )
        .api_route(
            "/cases/reprocess_dockets_for_all",
            post(reprocess_dockets),
        )
        .api_route(
            "/cases/download_missing_hashes_for_all",
            post(download_all_missing_hashes),
        )
        .api_route(
            "/write_s3_string",
            post_with(
                s3_routes::write_s3_file_string,
                s3_routes::write_s3_file_docs,
            ),
        )
        .api_route(
            "/write_s3_json",
            post_with(s3_routes::write_s3_file_json, s3_routes::write_s3_file_docs),
        )
        .api_route(
            "/direct_file_attachment_process",
            post_with(
                handle_directly_process_file_request,
                handle_directly_process_file_request_docs,
            ),
        )
        .api_route(
            "/cases/{state}/{jurisdiction_name}/purge_all",
            delete(s3_routes::recursive_delete_all_jurisdiction_data),
        );

    // Temporary routes are also admin routes
    define_temporary_routes(admin_routes)
}
