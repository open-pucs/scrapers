#![warn(unused_extern_crates)]
pub mod deduplication;
pub mod env_vars;
pub mod raw;
pub mod s3_stuff;

pub mod jurisdictions {
    use schemars::JsonSchema;
    use serde::{Deserialize, Serialize};

    #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone, Hash, PartialEq, Eq)]
    pub struct JurisdictionInfo {
        pub country: String,
        pub state: String,
        pub jurisdiction: String,
    }

    impl Default for JurisdictionInfo {
        fn default() -> Self {
            let unknown_static = "unknown";
            JurisdictionInfo {
                country: unknown_static.to_string(),
                state: unknown_static.to_string(),
                jurisdiction: unknown_static.to_string(),
            }
        }
    }

    impl JurisdictionInfo {
        pub fn new_usa(jurisdiction: &str, state: &str) -> Self {
            JurisdictionInfo {
                country: "usa".to_string(),
                state: state.to_string(),
                jurisdiction: jurisdiction.to_string(),
            }
        }
    }
}

