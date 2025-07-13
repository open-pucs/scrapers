use std::fmt;
use std::str::FromStr;
use std::{fs, path::Path, str};
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FileExtension {
    Pdf,
    Xlsx,
    Unknown(String),
}

impl FromStr for FileExtension {
    type Err = &'static str;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let first_element_extension = s.split_whitespace().next();
        let lowercase_validated_extension = match first_element_extension {
            Some(val) => val.to_lowercase(),
            None => return Err("Extension was empty"),
        };
        match &*lowercase_validated_extension {
            "pdf" => Ok(FileExtension::Pdf),
            "xlsx" => Ok(FileExtension::Xlsx),
            _ => Ok(FileExtension::Unknown(lowercase_validated_extension)),
        }
    }
}

use thiserror::Error;

#[derive(Error, Debug)]
pub enum FileValidationError {
    #[error("Error reading file: {0}")]
    ReadError(#[from] std::io::Error),
    #[error("File too short (expected at least 5 bytes)")]
    TooShort,
    #[error("Invalid PDF header (expected '%PDF-' at start)")]
    InvalidHeader,
    #[error("File is entirely UTF-8 encoded (expected binary PDF)")]
    UnexpectedUtf8Encoding,
}

impl FileExtension {
    pub fn is_valid_file<P: AsRef<Path>>(&self, path: P) -> Result<(), FileValidationError> {
        fn is_valid_pdf(path: &Path) -> Result<(), FileValidationError> {
            let contents = fs::read(path)?; // This returns ReadError on failure

            if contents.len() < 5 {
                return Err(FileValidationError::TooShort);
            }

            if &contents[0..5] != b"%PDF-" {
                return Err(FileValidationError::InvalidHeader);
            }

            if str::from_utf8(&contents).is_ok() {
                return Err(FileValidationError::UnexpectedUtf8Encoding);
            }

            Ok(())
        }

        match self {
            FileExtension::Pdf => is_valid_pdf(path.as_ref()),
            FileExtension::Xlsx => Ok(()),
            FileExtension::Unknown(_val) => Ok(()),
        }
    }
}

impl fmt::Display for FileExtension {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let displayed = match self {
            FileExtension::Pdf => "pdf".to_string(),
            FileExtension::Xlsx => "xlsx".to_string(),
            FileExtension::Unknown(ext) => ext.to_owned(),
        };
        write!(f, "{displayed}")
    }
}
use schemars::JsonSchema;
use serde::{Deserialize, Deserializer, Serialize, Serializer, de};
impl Serialize for FileExtension {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        // Use the existing Display implementation to convert to string
        serializer.serialize_str(&self.to_string())
    }
}

impl<'de> Deserialize<'de> for FileExtension {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        // Deserialize as string then parse using FromStr
        let s = String::deserialize(deserializer)?;
        s.parse::<FileExtension>().map_err(de::Error::custom)
    }
}

impl JsonSchema for FileExtension {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "FileExtension".into()
    }
    fn json_schema(generator: &mut schemars::SchemaGenerator) -> schemars::Schema {
        let schema = generator.subschema_for::<String>();
        schema
    }
}
