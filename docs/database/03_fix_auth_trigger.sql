-- ============================================================
-- LexLink: Fix auth.users trigger causing "Database error creating new user"
-- Run this entire script in Supabase SQL Editor (lexlink project)
-- ============================================================

-- Step 1: Check what triggers exist on auth.users
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'auth'
  AND event_object_table = 'users';

-- Step 2: Check existing handle_new_user function (if any)
SELECT prosrc
FROM pg_proc
WHERE proname = 'handle_new_user';

-- ============================================================
-- Step 3: Replace (or create) the handle_new_user function
-- This is the standard Supabase trigger that syncs auth.users
-- into public.profiles. We fix it to match our schema exactly
-- (no 'password' column, correct fields only).
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name, role, verification_status)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'role', 'layman'),
    'not_required'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Step 4: Drop old trigger if it exists (avoids duplicate trigger errors)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Step 5: Re-create the trigger cleanly
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE PROCEDURE public.handle_new_user();

-- ============================================================
-- Step 6: Verify the trigger is now registered
-- ============================================================
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'auth'
  AND event_object_table = 'users';
