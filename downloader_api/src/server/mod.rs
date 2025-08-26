use aide::{
    self,
    axum::{
        ApiRouter,
        routing::{delete, get, get_with, post, post_with},
    },
};
use direct_file_fetch::{
    handle_directly_process_file_request, handle_directly_process_file_request_docs,
};
use mycorrhiza_common::{llm_deepinfra::test_deepinfra, misc::is_env_var_true};
use std::sync::LazyLock;
use tracing::info;

use crate::server::{
    reprocess_all_handlers::{download_all_missing_hashes, reprocess_dockets},
    scraper_check_completed::get_completed_casedata_differential,
    temporary_routes::define_temporary_routes,
};

pub mod direct_file_fetch;
pub mod queue_routes;
pub mod reprocess_all_handlers;
pub mod s3_routes;
pub mod scraper_check_completed;
pub mod temporary_routes;

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
        .api_route("/test/deepinfra", get(test_deepinfra))
        .api_route(
            "/public/cases/{state}/{jurisdiction_name}/{case_name}",
            get(s3_routes::handle_processed_case_filing_from_s3),
        )
        .api_route(
            "/public/caselist/{state}/{jurisdiction_name}/all",
            get_with(
                s3_routes::handle_caselist_jurisdiction_fetch_all,
                s3_routes::handle_caselist_jurisdiction_fetch_all_docs,
            ),
        )
        .api_route(
            "/public/caselist/{state}/{jurisdiction_name}/casedata_differential",
            post(get_completed_casedata_differential),
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
        app = define_temporary_routes(app)
            .api_route(
                "/admin/cases/submit",
                post_with(
                    queue_routes::submit_case_to_queue_without_download,
                    queue_routes::submit_case_to_queue_docs,
                ),
            )
            .api_route(
                "/admin/cases/reprocess_dockets_for_all",
                post(reprocess_dockets),
            )
            .api_route(
                "/admin/cases/download_missing_hashes_for_all",
                post(download_all_missing_hashes),
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
            )
            .api_route(
                "/public/cases/{state}/{jurisdiction_name}/{case_name}",
                delete(s3_routes::delete_case_filing_from_s3),
            )
            .api_route(
                "/admin/cases/{state}/{jurisdiction_name}/purge_all",
                delete(s3_routes::recursive_delete_all_jurisdiction_data),
            );
    } else {
        info!("Public safe mode enabled, admin routes are disabled.");
    }

    info!("Routes defined successfully");
    app
}
