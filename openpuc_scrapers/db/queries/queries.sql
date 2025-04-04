-- :name last_updated_object_upsert :affected
INSERT INTO public.object_last_updated (
    country, 
    state,
    juristiction_name,
    object_type,
    object_name
) VALUES (
    :country,
    :state,
    :juristiction_name,
    :object_type,
    :object_name
)
ON CONFLICT (country, state, juristiction_name, object_type, object_name)
DO UPDATE SET indexed_at = NOW();

-- List outdated objects (all jurisdictions)
-- :name list_objects_last_updated_before :many
SELECT *
FROM public.object_last_updated
WHERE indexed_at_at < :indexed_before
ORDER BY updated_at ASC
LIMIT :limit;

-- List outdated objects for specific jurisdiction
-- :name list_objects_last_updated_before_for_jurisdiction :many
SELECT *
FROM public.object_last_updated
WHERE indexed_at < :indexed_before
  AND juristiction_name = :juristiction_name
ORDER BY updated_at ASC
LIMIT :limit;

