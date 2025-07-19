use super::*;
use crate::s3_stuff::make_s3_client;
use crate::types::{GenericCase, GenericFiling, GenericAttachment};
use chrono::Utc;

#[tokio::test]
async fn test_process_case() {
    let s3_client = make_s3_client().await;

    let case = GenericCase {
        case_number: "TEST-CASE-123".to_string(),
        filings: vec![
            GenericFiling {
                filed_date: Utc::now(),
                attachments: vec![
                    GenericAttachment {
                        name: "Test Attachment".to_string(),
                        url: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf".to_string(),
                        document_extension: Some("pdf".to_string()),
                        hash: None,
                        extra_metadata: Default::default(),
                    },
                ],
                ..Default::default()
            }
        ],
        ..Default::default()
    };

    let result = process_case(&case, &s3_client).await;
    assert!(result.is_ok());
}
