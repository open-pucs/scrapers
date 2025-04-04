-- Create DB Migration:
CREATE TABLE IF NOT EXISTS public.object_last_updated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    country VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    juristiction_name VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);


CREATE TABLE IF NOT EXISTS public.attachment_text_reprocessed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attachment_hash VARCHAR NOT NULL,
    update_type VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);
-- Upsert object last updated timestamp
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
DO UPDATE SET updated_at = NOW();

-- List outdated objects (all jurisdictions)
-- :name list_objects_last_updated_before :many
SELECT *
FROM public.object_last_updated
WHERE updated_at < :updated_before
ORDER BY updated_at ASC
LIMIT :limit;

-- List outdated objects for specific jurisdiction
-- :name list_objects_last_updated_before_for_jurisdiction :many
SELECT *
FROM public.object_last_updated
WHERE updated_at < :updated_before
  AND juristiction_name = :juristiction_name
ORDER BY updated_at ASC
LIMIT :limit;

