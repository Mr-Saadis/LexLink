-- ============================================
-- LexLink Profile Authentication Migration
-- ============================================

-- Remove password because authentication is handled
-- by Supabase Auth.
ALTER TABLE public.profiles
DROP COLUMN IF EXISTS password;

-- Add email if it does not already exist.
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Ensure email uses VARCHAR(255).
ALTER TABLE public.profiles
ALTER COLUMN email TYPE VARCHAR(255);

-- License number is optional because it is only
-- applicable to lawyers.
ALTER TABLE public.profiles
ALTER COLUMN license_no DROP NOT NULL;

-- Lawyer verification is not required at the
-- current stage.
ALTER TABLE public.profiles
ALTER COLUMN verification_status SET DEFAULT 'not_required';

-- NOTE:
-- CNIC is currently not set to NOT NULL because
-- existing profile records contain NULL CNIC values.