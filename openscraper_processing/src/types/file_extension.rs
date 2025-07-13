use std::fmt;
use std::str::FromStr;
use std::{fs, path::Path, str};
#[derive(Clone)]
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
    Utf8Encoded,
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
                return Err(FileValidationError::Utf8Encoded);
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

