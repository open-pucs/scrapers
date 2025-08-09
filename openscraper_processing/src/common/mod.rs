pub mod internet_check;

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
