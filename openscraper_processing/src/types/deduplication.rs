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

impl<Obj> DoubleDeduplicated<Obj> {
    pub fn make_double_deduplicated_with_keys<Key: Hash + Eq>(
        base: Vec<(Key, Obj)>,
        comparison: Vec<(Key, Obj)>,
    ) -> Self {
        enum SetMarker {
            Both,
            Base,
            Comparison,
        }
        fn combine_comparison_and_hashret(opt: &SetMarker) -> SetMarker {
            match opt {
                // If only in comparison it isnt in base
                SetMarker::Comparison => SetMarker::Comparison,
                // If it was marked as in base, and is in comparison, then its in both
                SetMarker::Base => SetMarker::Both,
                // If in both its still in both
                SetMarker::Both => SetMarker::Both,
            }
        }

        let mut hashmap: HashMap<Key, (SetMarker, Obj)> = HashMap::new();
        for (key, val) in base {
            hashmap.insert(key, (SetMarker::Base, val));
        }
        for (key, obj) in comparison {
            if let Some((mark, _)) = hashmap.get(&key) {
                let insert_marker = combine_comparison_and_hashret(mark);
                hashmap.insert(key, (insert_marker, obj));
            } else {
                hashmap.insert(key, (SetMarker::Comparison, obj));
            }
        }
        let mut return_deduped = DoubleDeduplicated::default();
        let _ = hashmap
            .into_iter()
            .map(|(_, (mark, obj))| match mark {
                SetMarker::Both => return_deduped.in_both.push(obj),
                SetMarker::Base => return_deduped.in_base.push(obj),
                SetMarker::Comparison => return_deduped.in_comparison.push(obj),
            })
            .count();
        return_deduped
    }
}
