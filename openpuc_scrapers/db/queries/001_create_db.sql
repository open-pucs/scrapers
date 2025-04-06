-- Create DB Migration:
CREATE TABLE IF NOT EXISTS public.object_last_updated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    country VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    juristiction_name VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);


CREATE TABLE IF NOT EXISTS public.attachment_text_reprocessed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attachment_hash VARCHAR NOT NULL,
    update_type VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);
