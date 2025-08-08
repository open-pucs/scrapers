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
fn map_empty<T: IsEmpty>(val: &T) -> Option<&T> {
    match val.is_empty() {
        true => None,
        false => Some(val),
    }
}
fn map_empty_mut<T: IsEmpty>(val: &mut T) -> Option<&mut T> {
    match val.is_empty() {
        true => None,
        false => Some(val),
    }
}

fn into_map_empty<T: IsEmpty>(val: T) -> Option<T> {
    match val.is_empty() {
        true => None,
        false => Some(val),
    }
}
