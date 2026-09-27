"""
LexLink - Admin Provisioning CLI Tool
======================================
Bootstraps the first Super-Admin or provisions additional admin accounts.

Uses the Supabase Service Role Key (Admin API) to:
  - Create auth.users entries directly (no email confirmation needed)
  - OR find an existing auth.users entry if the email already exists
  - Upsert the public.profiles row with role='admin'

Usage:
    python seed_admin.py --email admin@lexlink.pk --name "System Admin" --password "StrongPass123!"

Or interactive prompt:
    python seed_admin.py
"""

import sys
import os
import argparse
import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase_client import is_supabase_configured, get_supabase_client


def find_auth_user_by_email(client, email: str):
    """
    Searches auth.users for a user with the given email using the Admin API.
    Returns (user_id, found) tuple.
    """
    try:
        users = client.auth.admin.list_users()
        if isinstance(users, list):
            for u in users:
                u_email = getattr(u, "email", None) or ""
                if u_email.strip().lower() == email:
                    return str(u.id), True
    except Exception as e:
        print(f"[Supabase Auth] list_users notice: {e}")
    return None, False


def create_admin(email: str, name: str, password: str):
    if not is_supabase_configured():
        print("[Error] Supabase credentials not configured in backend/.env file!")
        sys.exit(1)

    clean_email = email.strip().lower()
    clean_name = name.strip()

    print(f"\nProvisioning Administrator: {clean_name} <{clean_email}>...")

    client = get_supabase_client()
    if not client:
        print("[Error] Could not initialize Supabase client.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Check existing profile
    # ------------------------------------------------------------------
    existing_profile = None
    try:
        res = client.table("profiles").select("*").eq("email", clean_email).execute()
        if res.data and len(res.data) > 0:
            existing_profile = res.data[0]
    except Exception as e:
        print(f"[Notice] Profile lookup: {e}")

    if existing_profile:
        current_role = existing_profile.get("role")
        print(f"[Info] Profile '{clean_email}' already exists (Role: {current_role}).")
        if current_role == "admin":
            print("[Info] This user is already an administrator. No action needed.")
            return
        confirm = input("Elevate this user to 'admin'? (y/n): ").strip().lower()
        if confirm == "y":
            client.table("profiles").update({"role": "admin", "name": clean_name}).eq("email", clean_email).execute()
            print(f"[Success] '{clean_email}' promoted to admin role!")
        else:
            print("[Aborted] No changes made.")
        return

    # ------------------------------------------------------------------
    # Step 2: Find or create Supabase Auth user
    # ------------------------------------------------------------------
    auth_user_id = None

    # 2a. Try Admin API create (bypasses email confirmation)
    try:
        res = client.auth.admin.create_user({
            "email": clean_email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"name": clean_name, "role": "admin"},
        })
        if res and res.user:
            auth_user_id = str(res.user.id)
            print(f"[Supabase Auth] New auth user created: {auth_user_id}")
    except Exception as e:
        err_str = str(e)
        print(f"[Supabase Auth] create_user: {err_str}")

        # 2b. Email already exists in auth.users — find them
        if "already" in err_str.lower() or "duplicate" in err_str.lower() or "Database error" in err_str:
            print("[Info] Email may already exist in auth.users. Searching...")
            auth_user_id, found = find_auth_user_by_email(client, clean_email)
            if found and auth_user_id:
                print(f"[Info] Found existing auth user: {auth_user_id}")
                # Update password for the existing user
                try:
                    client.auth.admin.update_user_by_id(auth_user_id, {"password": password, "email_confirm": True})
                    print("[Info] Auth user password updated.")
                except Exception as ue:
                    print(f"[Notice] Could not update password: {ue}")

    # 2c. Last resort: sign_up fallback
    if not auth_user_id:
        try:
            res = client.auth.sign_up({"email": clean_email, "password": password})
            if res and res.user:
                auth_user_id = str(res.user.id)
                print(f"[Supabase Auth] sign_up fallback user: {auth_user_id}")
        except Exception as e2:
            print(f"[Supabase Auth] sign_up: {e2}")

    if not auth_user_id:
        print("\n[Error] Could not resolve a Supabase Auth user for this email.")
        print("  Manual fix: Go to Supabase Dashboard -> Authentication -> Users")
        print("  Delete the entry for this email, then run this script again.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3: Upsert public.profiles (no password column per schema)
    # ------------------------------------------------------------------
    profile_payload = {
        "id": auth_user_id,
        "email": clean_email,
        "name": clean_name,
        "role": "admin",
        "verification_status": "not_required",
    }
    try:
        client.table("profiles").upsert(profile_payload, on_conflict="id").execute()
        print(f"[Supabase] Profile upserted: role='admin' for {clean_email}")
    except Exception as pe:
        print(f"[Supabase] Profile upsert error: {pe}")
        print("\n  Run this in Supabase SQL Editor to fix manually:")
        print(f"  INSERT INTO public.profiles (id, email, name, role, verification_status)")
        print(f"  VALUES ('{auth_user_id}', '{clean_email}', '{clean_name}', 'admin', 'not_required')")
        print(f"  ON CONFLICT (id) DO UPDATE SET role = 'admin', name = '{clean_name}';")

    print(f"\n[Success] Administrator provisioned!")
    print(f"  User ID : {auth_user_id}")
    print(f"  Email   : {clean_email}")
    print(f"  Name    : {clean_name}")
    print(f"  Role    : admin")
    print(f"\n  Login at the LexLink frontend with these credentials.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LexLink Admin Account Creation CLI")
    parser.add_argument("--email", help="Admin email (e.g. admin@lexlink.pk)")
    parser.add_argument("--name", help="Admin full name")
    parser.add_argument("--password", help="Admin password")

    args = parser.parse_args()

    email = args.email or input("Enter Admin Email: ").strip()
    name = args.name or input("Enter Admin Full Name: ").strip()
    password = args.password or getpass.getpass("Enter Admin Password: ").strip()

    if not email or not name or not password:
        print("[Error] Email, Name, and Password are all required.")
        sys.exit(1)

    create_admin(email=email, name=name, password=password)
