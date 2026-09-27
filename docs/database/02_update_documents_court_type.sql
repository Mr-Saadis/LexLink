-- ============================================================
-- Simple SQL Migration: Rename to declared_court_type & Clean Metadata
-- ============================================================

-- 1. Rename column `court_type` to `declared_court_type`
ALTER TABLE public.documents 
RENAME COLUMN court_type TO declared_court_type;

-- 2. Remove redundant `court_type` key from `metadata` JSONB column
UPDATE public.documents
SET metadata = metadata - 'court_type' - 'court_type_declared'
WHERE metadata IS NOT NULL;

-- 3. Verify changes
SELECT id, title, declared_court_type, metadata 
FROM public.documents 
LIMIT 5;
