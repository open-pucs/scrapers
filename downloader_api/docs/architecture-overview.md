# Downloader API Architecture Overview

## Purpose
The Downloader API is a component of the openscrapers library designed to efficiently and cheaply process government documents at scale. It handles the ingestion, processing, and storage of legal case data and attachments.

## Key Components

1. **API Server** - Built with Axum and Aide for documentation
2. **Data Processing Pipeline** - Converts raw data to processed formats
3. **S3 Integration** - Stores raw and processed data
4. **Background Workers** - Process tasks asynchronously
5. **Type System** - Strongly typed data structures for legal documents

## Core Technologies

- **Language**: Rust
- **Framework**: Axum (web framework)
- **Storage**: AWS S3
- **Serialization**: Serde
- **Documentation**: Aide/OpenAPI
- **Async Runtime**: Tokio
- **Tracing**: OpenTelemetry

## High-Level Flow

1. Raw case data is submitted via API or fetched from sources
2. Data is validated and stored in S3 as raw objects
3. Background workers process raw data into standardized formats
4. Processed data is stored back in S3
5. Processed data is made available via API endpoints
6. Attachments are downloaded, processed, and stored separately

## Security Considerations

- Public safe mode can disable admin routes
- CORS is configured for cross-origin requests
- Tracing and logging for observability