# API Routes Documentation

## Health and Test Routes

- `GET /` - Health check endpoint
- `GET /health` - Health check endpoint
- `GET /test/deepinfra` - Test DeepInfra API connectivity

## Public Routes (Available in Safe Mode)

### Case Data Access
- `GET /public/cases/{state}/{jurisdiction_name}/{case_name}` - Fetch processed case filing data
- `GET /public/caselist/{state}/{jurisdiction_name}/all` - List all cases for a jurisdiction (paginated)
- `POST /public/caselist/{state}/{jurisdiction_name}/casedata_differential` - Get case data differential

### Attachment Access
- `GET /public/raw_attachments/{blake2b_hash}/obj` - Fetch attachment metadata
- `GET /public/raw_attachments/{blake2b_hash}/raw` - Fetch attachment file content
- `GET /public/read_openscrapers_s3_file/{path}` - Read arbitrary file from S3

## Admin Routes (Disabled in Safe Mode)

### Case Management
- `POST /admin/cases/submit` - Submit a case to the processing queue
- `POST /admin/cases/reprocess_dockets_for_all` - Reprocess all dockets
- `POST /admin/cases/download_missing_hashes_for_all` - Download missing attachment hashes
- `DELETE /public/cases/{state}/{jurisdiction_name}/{case_name}` - Delete a case filing
- `DELETE /admin/cases/{state}/{jurisdiction_name}/purge_all` - Delete all data for a jurisdiction

### S3 Management
- `POST /admin/write_s3_string` - Write string content to S3
- `POST /admin/write_s3_json` - Write JSON content to S3

### Direct Processing
- `POST /admin/direct_file_attachment_process` - Process a file attachment directly

## Route Parameters

### CasePath
- `state` (String) - The state of the jurisdiction
- `jurisdiction_name` (String) - The name of the jurisdiction
- `case_name` (String) - The name of the case

### JurisdictionPath
- `state` (String) - The state of the jurisdiction
- `jurisdiction_name` (String) - The name of the jurisdiction

### AttachmentPath
- `blake2b_hash` (String) - The blake2b hash of the attachment

### Pagination
- `limit` (Integer) - Number of items to return
- `offset` (Integer) - Number of items to skip

## Response Formats

All responses are JSON unless otherwise specified. Error responses include descriptive error messages.