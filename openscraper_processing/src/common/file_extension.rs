use std::convert::Infallible;
use std::fmt::{self, Binary, Display};
use std::str::FromStr;
use std::{fs, path::Path, str};
use tracing::warn;

macro_rules! static_extensions {
    ($($variant:ident => $ext_str:expr),* $(,)?) => {
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
        pub enum StaticExtension {
            $($variant),*
        }

        impl StaticExtension {
            /// Returns the extension string exactly as it was given.
            pub const fn get_static_str(&self) -> &'static str {
                match self {
                    $(Self::$variant => $ext_str),*
                }
            }

            /// Case-sensitive comparison; returns `None` if no match.
            pub fn from_str(s: &str) -> Option<Self> {
                match s {
                    $($ext_str => Some(Self::$variant),)*
                    _ => None,
                }
            }
        }
    };
}

// ---- Define the extensions you care about here ------------
static_extensions! {
    Pdf  => "pdf",
    Xlsx => "xlsx",
    Md   => "md",
    Html => "html",
    Png  => "png",
}
#[derive(Clone, Copy, Debug)]
pub enum FileEncoding {
    Binary,
    Utf8,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Default)]
pub enum FileExtension {
    Static(StaticExtension),
    Unknown(String),
    #[default]
    Empty,
}

impl FileExtension {
    fn is_empty(&self) -> bool {
        matches!(self, Self::Empty)
    }
    fn get_encoding(&self) -> FileEncoding {
        let Self::Static(static_ext) = self else {
            return FileEncoding::Unknown;
        };
        match static_ext {
            StaticExtension::Pdf => FileEncoding::Binary,
            StaticExtension::Xlsx => FileEncoding::Binary,
            StaticExtension::Html => FileEncoding::Utf8,
            _ => FileEncoding::Unknown,
        }
    }
    fn to_str(&self) -> &str {
        match self {
            Self::Static(val) => val.get_static_str(),
            Self::Unknown(val) => val,
            Self::Empty => "",
        }
    }
}

impl Display for FileExtension {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.to_str())
    }
}

impl FromStr for FileExtension {
    type Err = Infallible;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let intiial_fragment =
            into_fmap_empty(s.split_whitespace().next().map(|val| val.to_lowercase()));
        let Some(parsed) = intiial_fragment else {
            return Ok(Self::Empty);
        };
        let static_opt = StaticExtension::from_str(&parsed).map(Self::Static);
        Ok(static_opt.unwrap_or_else(|| Self::Unknown(s.to_owned())))
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
            FileExtension::Static(StaticExtension::Pdf) => is_valid_pdf_contents(contents),
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

use crate::common::misc::{fmap_empty, into_fmap_empty};
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
