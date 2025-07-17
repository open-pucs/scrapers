use std::{env, sync::LazyLock};

pub static OPENSCRAPERS_S3_CLOUD_REGION: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_CLOUD_REGION").unwrap_or_else(|_| "sfo3".to_string())
});

pub static OPENSCRAPERS_S3_ENDPOINT: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_ENDPOINT")
        .unwrap_or_else(|_| "https://sfo3.digitaloceanspaces.com".to_string())
});

pub static OPENSCRAPERS_S3_OBJECT_BUCKET: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_OBJECT_BUCKET").unwrap_or_else(|_| "opescrapers".to_string())
});

pub static OPENSCRAPERS_S3_ACCESS_KEY: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_ACCESS_KEY").expect("OPENSCRAPERS_S3_ACCESS_KEY must be set")
});

pub static OPENSCRAPERS_S3_SECRET_KEY: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_SECRET_KEY").expect("OPENSCRAPERS_S3_SECRET_KEY must be set")
});

pub static OPENSCRAPERS_REDIS_DOMAIN: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_REDIS_DOMAIN").unwrap_or_else(|_| "http://localhost:6379".to_string())
});

pub static CRIMSON_URL: LazyLock<String> = LazyLock::new(|| {
    env::var("CRIMSON_URL").unwrap_or_else(|_| "http://localhost:14423".to_string())
});
