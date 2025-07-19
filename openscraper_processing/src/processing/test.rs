use super::*;
use crate::s3_stuff::make_s3_client;
use crate::types::{GenericAttachment, GenericCase, GenericFiling, JurisdictionInfo};
use chrono::Utc;

#[tokio::test]
async fn test_process_case() {
    tracing_subscriber::fmt()
        // enable everything
        .with_max_level(tracing::Level::INFO)
        .compact()
        // Display source code file paths
        .with_file(true)
        // Display source code line numbers
        .with_line_number(true)
        // Display the thread ID an event was recorded on
        .with_thread_ids(true)
        // Don't display the event's target (module path)
        .with_target(false)
        // sets this to be the default, global collector for this application.
        .init();
    let s3_client = make_s3_client().await;

    let case = GenericCase {
        case_number: "TEST-CASE-123".to_string(),
        filings: vec![GenericFiling {
            filed_date: Utc::now(),
            attachments: vec![GenericAttachment {
                name: "Test Attachment".to_string(),
                url: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
                    .to_string(),
                document_extension: Some("pdf".to_string()),
                hash: None,
                extra_metadata: Default::default(),
            }],
            ..Default::default()
        }],
        ..Default::default()
    };
    let jurisdiction = JurisdictionInfo::new_usa("test", "test");
    let casewith = CaseWithJurisdiction { case, jurisdiction };

    let result = process_case(&casewith, &s3_client).await;
    assert!(result.is_ok());
}
