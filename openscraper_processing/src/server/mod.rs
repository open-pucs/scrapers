use aide::{
    self,
    axum::{
        ApiRouter,
        routing::{delete, get, get_with, post_with},
    },
};
use direct_file_fetch::{
    handle_directly_process_file_request, handle_directly_process_file_request_docs,
};
use std::sync::LazyLock;
use tracing::info;

use crate::common::misc::is_env_var_true;

pub mod direct_file_fetch;
pub mod queue_routes;
pub mod s3_routes;

static PUBLIC_SAFE_MODE: LazyLock<bool> = LazyLock::new(|| is_env_var_true("PUBLIC_SAFE_MODE"));

async fn return_healthy() -> &'static str {
    "service is healthy"
}

pub fn define_routes() -> ApiRouter {
    println!("Defining API Routes but without tracing.");
    info!("Defining API Routes");
    let mut app = ApiRouter::new()
        .api_route("/", get(return_healthy))
        .api_route("/health", get(return_healthy))
        .api_route(
            "/public/cases/{state}/{jurisdiction_name}/{case_name}",
            get_with(
                s3_routes::handle_case_filing_from_s3,
                s3_routes::handle_case_filing_from_s3_docs,
            )
            .delete(s3_routes::delete_case_filing_from_s3),
        )
        .api_route(
            "/public/cases/{state}/{jurisdiction_name}/purge_all",
            delete(s3_routes::recursive_delete_all_jurisdiction_data),
        )
        .api_route(
            "/public/caselist/{state}/{jurisdiction_name}/all",
            get_with(
                s3_routes::handle_caselist_jurisdiction_fetch_all,
                s3_routes::handle_caselist_jurisdiction_fetch_all_docs,
            )
            .delete(s3_routes::delete_case_filing_from_s3),
        )
        .api_route(
            "/public/raw_attachments/{blake2b_hash}/obj",
            get_with(
                s3_routes::handle_attachment_data_from_s3,
                s3_routes::handle_attachment_data_from_s3_docs,
            ),
        )
        .api_route(
            "/public/raw_attachments/{blake2b_hash}/raw",
            get_with(
                s3_routes::handle_attachment_file_from_s3,
                s3_routes::handle_attachment_file_from_s3_docs,
            ),
        )
        .api_route(
            "/public/read_openscrapers_s3_file/{path}",
            get_with(
                s3_routes::read_openscrapers_s3_file,
                s3_routes::read_s3_file_docs,
            ),
        );

    if !*PUBLIC_SAFE_MODE {
        app = app
            .api_route(
                "/admin/cases/submit",
                post_with(
                    queue_routes::submit_case_to_queue,
                    queue_routes::submit_case_to_queue_docs,
                ),
            )
            .api_route(
                "/admin/write_s3_string",
                post_with(
                    s3_routes::write_s3_file_string,
                    s3_routes::write_s3_file_docs,
                ),
            )
            .api_route(
                "/admin/write_s3_json",
                post_with(s3_routes::write_s3_file_json, s3_routes::write_s3_file_docs),
            )
            .api_route(
                "/admin/direct_file_attachment_process",
                post_with(
                    handle_directly_process_file_request,
                    handle_directly_process_file_request_docs,
                ),
            );
    } else {
        info!("Public safe mode enabled, admin routes are disabled.");
    }

    info!("Routes defined successfully");
    app
}
