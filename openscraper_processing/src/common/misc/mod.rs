use std::time::Duration;

pub mod internet_check;

pub fn prettyprint_duration(dur: Duration) -> String {
    let total_secs = dur.as_secs();
    let hours = total_secs / 3600;
    let minutes = (total_secs % 3600) / 60;
    let seconds = total_secs % 60;
    let millis = dur.subsec_millis();

    if hours > 0 {
        format!("{}h {}m {}.{:03}s", hours, minutes, seconds, millis)
    } else if minutes > 0 {
        format!("{}m {}.{:03}s", minutes, seconds, millis)
    } else if seconds > 0 || millis >= 100 {
        format!("{}.{:03}s", seconds, millis)
    } else {
        format!("{}ms", millis)
    }
}

pub fn is_env_var_true(var_name: &str) -> bool {
    let Ok(var) = std::env::var(var_name) else {
        return false;
    };
    if var.is_empty() {
        return false;
    }
    if var == "0" {
        return false;
    }
    if var == "false" {
        return false;
    }
    true
}

pub trait IsEmpty {
    fn is_empty(&self) -> bool;
}

impl IsEmpty for str {
    #[inline]
    fn is_empty(&self) -> bool {
        self.is_empty()
    }
}
impl IsEmpty for String {
    #[inline]
    fn is_empty(&self) -> bool {
        self.is_empty()
    }
}
impl<T> IsEmpty for [T] {
    #[inline]
    fn is_empty(&self) -> bool {
        self.is_empty()
    }
}
impl<T> IsEmpty for Vec<T> {
    #[inline]
    fn is_empty(&self) -> bool {
        self.is_empty()
    }
}
pub fn map_empty<T: IsEmpty + ?Sized>(val: &T) -> Option<&T> {
    match val.is_empty() {
        true => None,
        false => Some(val),
    }
}

pub fn fmap_empty<T: IsEmpty + ?Sized>(val: Option<&T>) -> Option<&T> {
    match val {
        None => None,
        Some(val) => match val.is_empty() {
            true => None,
            false => Some(val),
        },
    }
}
pub fn into_fmap_empty<T: IsEmpty>(val: Option<T>) -> Option<T> {
    match val {
        None => None,
        Some(val) => match val.is_empty() {
            true => None,
            false => Some(val),
        },
    }
}
