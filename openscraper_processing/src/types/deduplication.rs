use std::{collections::HashMap, hash::Hash, vec};

#[derive(Clone)]
pub struct DoubleDeduplicated<T> {
    pub in_both: Vec<T>,
    pub in_base: Vec<T>,
    pub in_comparison: Vec<T>,
}

impl<T> Default for DoubleDeduplicated<T> {
    fn default() -> Self {
        DoubleDeduplicated {
            in_both: vec![],
            in_base: vec![],
            in_comparison: vec![],
        }
    }
}

impl<T: Hash + Eq> DoubleDeduplicated<T> {
    pub fn make_double_deduplicated(base: Vec<T>, comparison: Vec<T>) -> Self {
        enum SetMarker {
            Both,
            Base,
            Comparison,
        }
        fn combine_comparison_and_hashret(opt: Option<&SetMarker>) -> SetMarker {
            match opt {
                // If not in there at all it isnt in base.
                None => SetMarker::Comparison,
                // If only in comparison it isnt in base
                Some(SetMarker::Comparison) => SetMarker::Comparison,
                // If it was marked as in base, and is in comparison, then its in both
                Some(SetMarker::Base) => SetMarker::Both,
                // If in both its still in both
                Some(SetMarker::Both) => SetMarker::Both,
            }
        }

        let mut hashmap: HashMap<T, SetMarker> = HashMap::new();
        for val in base {
            hashmap.insert(val, SetMarker::Base);
        }
        for val in comparison {
            let insert_marker = combine_comparison_and_hashret(hashmap.get(&val));
            hashmap.insert(val, insert_marker);
        }
        let mut return_deduped = DoubleDeduplicated::<T>::default();
        let x = hashmap
            .into_iter()
            .map(|(val, marker)| match marker {
                SetMarker::Both => return_deduped.in_both.push(val),
                SetMarker::Base => return_deduped.in_base.push(val),
                SetMarker::Comparison => return_deduped.in_comparison.push(val),
            })
            .count();
        return_deduped
    }
}
