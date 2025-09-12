use std::{env, sync::LazyLock};

use mycorrhiza_common::s3_generic::{S3Credentials, S3EnvNames, make_s3_lazylock};

pub static OPENSCRAPERS_S3_OBJECT_BUCKET: LazyLock<String> = LazyLock::new(|| {
    env::var("OPENSCRAPERS_S3_OBJECT_BUCKET").unwrap_or_else(|_| "openscrapers".to_string())
});

struct S3Envs {}
impl S3EnvNames for S3Envs {
    const REGION_ENV: &str = "OPENSCRAPERS_S3_CLOUD_REGION";
    const ENDPOINT_ENV: &str = "OPENSCRAPERS_S3_ENDPOINT";
    const ACCESS_ENV: &str = "OPENSCRAPERS_S3_ACCESS_KEY";
    const SECRET_ENV: &str = "OPENSCRAPERS_S3_SECRET_KEY";
}

pub static OPENSCRAPERS_S3: LazyLock<S3Credentials> = make_s3_lazylock::<S3Envs>();

// pub static OPENSCRAPERS_REDIS_DOMAIN: LazyLock<String> = LazyLock::new(|| {
//     env::var("OPENSCRAPERS_REDIS_DOMAIN").unwrap_or_else(|_| "localhost:6379".to_string())
// });
//
// pub static OPENSCRAPERS_REDIS_STRING: LazyLock<String> =
//     LazyLock::new(|| format!("redis://{}", *OPENSCRAPERS_REDIS_DOMAIN));

pub static CRIMSON_URL: LazyLock<String> = LazyLock::new(|| {
    env::var("CRIMSON_URL").unwrap_or_else(|_| "http://localhost:14423".to_string())
});
