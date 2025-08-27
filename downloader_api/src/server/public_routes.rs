use aide::axum::{
    routing::{get_with, post},
    ApiRouter,
};

use crate::server::scraper_check_completed::get_completed_casedata_differential;
use crate::server::s3_routes;

pub fn create_public_router() -> ApiRouter {
    ApiRouter::new()
        .api_route(
            "/cases/{state}/{jurisdiction_name}/{case_name}",
            get_with(
                s3_routes::handle_processed_case_filing_from_s3,
                s3_routes::handle_processed_case_filing_from_s3_docs,
            ),
        )
        .api_route(
            "/caselist/{state}/{jurisdiction_name}/all",
            get_with(
                s3_routes::handle_caselist_jurisdiction_fetch_all,
                s3_routes::handle_caselist_jurisdiction_fetch_all_docs,
            ),
        )
        .api_route(
            "/caselist/{state}/{jurisdiction_name}/casedata_differential",
            post(get_completed_casedata_differential),
        )
        .api_route(
            "/raw_attachments/{blake2b_hash}/obj",
            get_with(
                s3_routes::handle_attachment_data_from_s3,
                s3_routes::handle_attachment_data_from_s3_docs,
            ),
        )
        .api_route(
            "/raw_attachments/{blake2b_hash}/raw",
            get_with(
                s3_routes::handle_attachment_file_from_s3,
                s3_routes::handle_attachment_file_from_s3_docs,
            ),
        )
        .api_route(
            "/read_openscrapers_s3_file/{path}",
            get_with(
                s3_routes::read_openscrapers_s3_file,
                s3_routes::read_s3_file_docs,
            ),
        )
}
