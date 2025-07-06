# Refactor Plan

### 1. Python (`generic_pipeline_wrappers.py`)
*   First, I will remove the `async_shit` function and the `asyncio.run` call from the `process_case` function.
*   Then, I will add a Redis client to the Python script and push the `GenericCase` and `GenericFiling` data to a Redis queue as a JSON object.
*   Finally, I will refactor the `process_case` function to return a success signal instead of a `GenericCase` object.

### 2. Rust (`worker.rs`)
*   First, I will add a Redis client to the Rust worker to pull messages from the Redis queue.
*   Then, I will create Rust structs that mirror the Python `GenericCase` and `GenericFiling` data models and deserialize the JSON object from Redis into these structs.
*   Next, I will port the business logic of the `process_generic_filing` function from the `raw_attachment_handling.py` script to the Rust worker. This includes fetching and processing attachments and saving the processed data to S3 and the database.
*   Finally, I will update the `Cargo.toml` file to include the necessary dependencies for Redis, HTTP requests, and AWS S3.

### 3. Data Models
*   I will define a JSON structure based on the Python `GenericCase` and `GenericFiling` models to be passed through Redis.
*   Then, I will create corresponding structs in the Rust worker to ensure seamless data transfer and processing.