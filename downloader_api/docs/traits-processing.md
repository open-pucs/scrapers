# Traits and Processing Implementation

## Core Processing Traits Implementation

### ProcessFrom Implementations (src/types/openscraper_data_traits.rs)

#### ProcessFrom<RawGenericDocket> for ProcessedGenericDocket

This implementation transforms a raw docket into a processed docket:

1. Validates and normalizes the opened date by checking filing dates
2. Matches raw filings to processed filings (for caching)
3. Processes filings concurrently (up to 5 at a time)
4. Builds a HashMap of processed filings indexed by ID
5. Creates the final processed docket with timestamps

#### ProcessFrom<RawGenericFiling> for ProcessedGenericFiling

This implementation transforms a raw filing into a processed filing:

1. Matches raw attachments to processed attachments (for caching)
2. Processes attachments concurrently (up to 5 at a time)
3. Processes organization and individual authors:
   - Uses cached authors if available
   - Splits and fixes author blobs using LLM if needed
   - Cleans up author lists if already split
4. Creates the processed filing with indexed data

#### ProcessFrom<RawGenericAttachment> for ProcessedGenericAttachment

This implementation transforms a raw attachment into a processed attachment:

1. Reuses existing attachment ID from cache or generates new one
2. Reuses hash from input or cache
3. Creates processed attachment with indexed data

### DownloadIncomplete Implementations (src/processing/mod.rs)

#### DownloadIncomplete for ProcessedGenericDocket

Downloads all incomplete attachments for a docket:

1. Creates a reference list of attachments without hashes
2. Wraps each attachment's DownloadIncomplete implementation
3. Processes attachments concurrently (up to 2 at a time)
4. Logs successful completion

## Processing Functions

### process_case (src/processing/mod.rs)

Main function for processing a case:

1. Uploads raw case data to S3
2. Downloads cached processed case data from S3 (if exists)
3. Processes raw case into processed case using ProcessFrom trait
4. Uploads processed case to S3

### make_reflist_of_attachments_without_hash (src/processing/mod.rs)

Helper function that creates a mutable reference list of all attachments in a docket that don't have hashes.

## Background Task Processing

### ProcessCaseWithoutDownload (src/case_worker.rs)

A task that processes a case without downloading attachments:

1. Implements ExecuteUserTask trait for background processing
2. Creates S3 client
3. Extracts case and jurisdiction data
4. Calls process_case with the data

### ReprocessDocketInfo (src/processing/mod.rs)

A task that reprocesses a docket:

1. Implements ExecuteUserTask trait for background processing
2. Downloads raw case data from S3
3. Downloads cached processed case data from S3 (if exists)
4. Optionally skips cached data based on timestamp
5. Processes raw case into processed case using ProcessFrom trait
6. Uploads processed case to S3

## Attachment Processing (src/processing/attachments.rs)

Attachments are processed separately from case data:

1. Attachments without hashes are identified
2. Raw attachment files are downloaded
3. Content is processed (e.g., PDF to text)
4. Processed content is stored in S3
5. Attachment metadata is updated with hashes

## File Fetching (src/processing/file_fetching.rs)

Handles downloading files from URLs:

1. Fetches files from provided URLs
2. Calculates Blake2b hash of content
3. Stores files temporarily
4. Returns file path and hash

## LLM Processing (src/processing/llm_prompts.rs)

Uses LLMs to process author names:

1. `split_and_fix_author_blob` - Splits and fixes author name blobs
2. `clean_up_author_list` - Cleans up individual author names

## Matching Functions (src/processing/match_raw_processed.rs)

Matches raw data with processed data for caching:

1. `match_raw_fillings_to_processed_fillings` - Matches raw filings to processed filings
2. `match_raw_attaches_to_processed_attaches` - Matches raw attachments to processed attachments

## S3 Integration (src/s3_stuff.rs)

### CannonicalS3ObjectLocation Trait

Defines how objects are stored in S3:

```rust
pub trait CannonicalS3ObjectLocation: serde::Serialize + serde::de::DeserializeOwned {
    type AddressInfo;
    fn generate_object_key(addr: &Self::AddressInfo) -> String;
}
```

### Implementations

#### RawAttachment
- Object key: `raw/metadata/{hash}.json`

#### RawGenericDocket
- Object key: `objects_raw/{country}/{state}/{jurisdiction}/{case_name}`

#### ProcessedGenericDocket
- Object key: `objects/{country}/{state}/{jurisdiction}/{case_name}`

### Key Functions

- `download_openscrapers_object` - Downloads JSON objects from S3
- `upload_object` - Uploads JSON objects to S3
- `delete_openscrapers_s3_object` - Deletes objects from S3
- `fetch_attachment_file_from_s3` - Downloads attachment file content
- `does_openscrapers_attachment_exist` - Checks if attachment exists
- `list_processed_cases_for_jurisdiction` - Lists processed cases
- `list_raw_cases_for_jurisdiction` - Lists raw cases
- `push_raw_attach_file_to_s3` - Uploads raw attachment files

## Data Deduplication (src/types/deduplication.rs)

Handles deduplication of data based on various criteria:

1. Docket deduplication based on government ID
2. Filing deduplication based on government ID
3. Attachment deduplication based on hash

## Pagination (src/types/pagination.rs)

Handles pagination of large result sets:

1. `PaginationData` struct for limit/offset
2. `make_paginated_subslice` function for creating paginated results

## Environment Variables (src/types/env_vars.rs)

Manages environment variable configuration:

1. `OPENSCRAPERS_S3` - S3 configuration
2. `OPENSCRAPERS_S3_OBJECT_BUCKET` - S3 bucket name
3. `PUBLIC_SAFE_MODE` - Disables admin routes when true