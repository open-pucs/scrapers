use std::fmt;
use std::str::FromStr;
use std::{fs, path::Path, str};
use tracing::warn;

#[derive(Debug, thiserror::Error)]
#[error("File Extension was empty or contained only whitespace")]
pub struct EmptyExtensionError {}
macro_rules! define_file_extensions {
    ($($variant:ident => ($ext_str:expr, $encoding:expr)),* $(,)?) => {
        #[derive(Clone, Debug, PartialEq, Eq)]
        pub enum FileExtension {
            $($variant),*,
            Unknown(String),
        }

        impl FromStr for FileExtension {
            type Err = EmptyExtensionError;

            fn from_str(s: &str) -> Result<Self, Self::Err> {
                let ext = s.split_whitespace().next()
                    .map(|s| s.to_lowercase())
                    .ok_or(EmptyExtensionError{})?;

                match ext.as_str() {
                    $(
                        $ext_str => Ok(FileExtension::$variant),
                    )*
                    _ => {
                        warn!(extension=%ext,"Encountered unknown file extension, if not invalid, consider adding it.");
                        Ok(FileExtension::Unknown(ext))},
                }
            }
        }

        impl fmt::Display for FileExtension {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                match self {
                    $(
                        FileExtension::$variant => write!(f, $ext_str),
                    )*
                    FileExtension::Unknown(ext) => write!(f, "{}", ext),
                }
            }
        }

        impl FileExtension {
            pub fn get_encoding(&self) -> FileEncoding {
                match self {
                    $(
                        FileExtension::$variant => $encoding,
                    )*
                    FileExtension::Unknown(_) => FileEncoding::Unknown,
                }
            }
        }
    };
}

#[derive(Clone, Copy, Debug)]
pub enum FileEncoding {
    Binary,
    Utf8,
    Unknown,
}

// Define all supported file extensions. Second variable should be the encoding of the file.
define_file_extensions! {
    Pdf => ("pdf", FileEncoding::Binary),
    Xlsx => ("xlsx", FileEncoding::Unknown),
    Md => ("md", FileEncoding::Utf8),
    Html => ("html", FileEncoding::Utf8),
    Docx => ("docx", FileEncoding::Unknown),
    Png => ("png", FileEncoding::Binary),
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
    #[error("File is not binary encoded (got a utf8 encoded file)")]
    BinaryWanted,
    #[error("File is not utf8 encoded")]
    Utf8Wanted,
}

impl FileExtension {
    pub fn is_valid_file_contents(&self, contents: &[u8]) -> Result<(), FileValidationError> {
        self.get_encoding().is_valid_file_contents(contents)?;
        fn is_valid_pdf_contents(contents: &[u8]) -> Result<(), FileValidationError> {
            if contents.len() < 5 {
                return Err(FileValidationError::TooShort);
            }
            if &contents[0..5] != b"%PDF-" {
                return Err(FileValidationError::InvalidHeader);
            }
            Ok(())
        }

        match self {
            FileExtension::Pdf => is_valid_pdf_contents(contents),
            _ => Ok(()),
        }
    }
    pub fn is_valid_file<P: AsRef<Path>>(&self, path: P) -> Result<(), FileValidationError> {
        let contents = fs::read(path)?; // This returns ReadError on failure
        self.is_valid_file_contents(&contents)
    }
}
impl FileEncoding {
    pub fn is_valid_file_contents(&self, contents: &[u8]) -> Result<(), FileValidationError> {
        match self {
            Self::Unknown => Ok(()),
            Self::Binary => {
                let is_not_utf8 = str::from_utf8(contents).is_err();
                if is_not_utf8 {
                    Ok(())
                } else {
                    Err(FileValidationError::BinaryWanted)
                }
            }

            Self::Utf8 => {
                let is_utf8 = str::from_utf8(contents).is_ok();
                if is_utf8 {
                    Ok(())
                } else {
                    Err(FileValidationError::Utf8Wanted)
                }
            }
        }
    }
}

use schemars::{JsonSchema, json_schema};
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
    fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
        json_schema!({
        "type": "string",
        "title": "File Extension",
        "description": "File extension. Should be lowercase with no whitespace, but can parse other values."
        })
    }
}
