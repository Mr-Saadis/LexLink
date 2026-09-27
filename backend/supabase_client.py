# backend/supabase_client.py
"""
Supabase Client & Database Services for LexLink Ingestion Pipeline.
Handles direct insertion into `public.documents` and `public.chunks`.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file from the current directory or backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_KEY", "").strip()
)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Returns a singleton instance of the Supabase client.
    Returns None if credentials are not configured yet.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or "your-project" in SUPABASE_URL or not SUPABASE_KEY or "your-" in SUPABASE_KEY:
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        print(f"[Supabase] Connection error: {e}")
        return None


def is_supabase_configured() -> bool:
    """Checks if valid Supabase credentials exist in .env"""
    return bool(
        SUPABASE_URL
        and "your-project" not in SUPABASE_URL
        and SUPABASE_KEY
        and "your-" not in SUPABASE_KEY
    )


JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key_lexlink_2026_dev")


def _issue_jwt(user_id: str, email: str, name: str, role: str) -> str:
    """Issues a signed HS256 JWT for an authenticated user."""
    import jwt
    import datetime
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "role": role,
        "exp": now_utc + datetime.timedelta(days=7),
        "iat": now_utc,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticates a user via Supabase Auth (GoTrue) and returns a signed JWT
    enriched with profile role data.
    Passwords are managed by Supabase Auth — not stored in public.profiles.
    """
    clean_email = (email or "").strip().lower()
    clean_password = (password or "").strip()

    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.auth.sign_in_with_password({"email": clean_email, "password": clean_password})
        if not res or not res.session or not res.user:
            return None

        user_id = str(res.user.id)
        supabase_token = res.session.access_token

        # Fetch application profile (role, name, etc.)
        profile = {}
        try:
            prof = client.table("profiles").select("*").eq("id", user_id).execute()
            if prof.data:
                profile = prof.data[0]
        except Exception:
            pass

        user_name = profile.get("name") or res.user.email.split("@")[0]
        user_role = profile.get("role", "layman")
        verification_status = profile.get("verification_status", "not_required")

        # Issue our own role-enriched JWT on top of the Supabase session
        token = _issue_jwt(user_id, clean_email, user_name, user_role)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": clean_email,
                "name": user_name,
                "role": user_role,
                "verification_status": verification_status,
            },
        }
    except Exception as e:
        print(f"[Supabase Auth] Login error: {e}")
        return None


def register_user(
    email: str,
    password: str,
    name: str,
    role: str = "layman",
    license_no: Optional[str] = None,
    cnic: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Registers a new user via Supabase Auth (GoTrue) and creates their application
    profile in public.profiles. Passwords are stored in auth.users only — not in profiles.
    """
    client = get_supabase_client()
    if not client:
        return None
    try:
        clean_email = email.strip().lower()
        role = role.lower().strip()
        if role not in ("layman", "lawyer", "admin"):
            role = "layman"

        verification_status = "pending" if role == "lawyer" else "not_required"

        # 1. Create Supabase Auth user (password handled by Supabase, never stored in profiles)
        user_id = None
        try:
            res = client.auth.sign_up({"email": clean_email, "password": password})
            if res and res.user:
                user_id = str(res.user.id)
        except Exception as se:
            print(f"[Supabase Auth] sign_up notice: {se}")

        if not user_id:
            import uuid
            user_id = str(uuid.uuid4())
            print(f"[Supabase Auth] Using fallback UUID for profile: {user_id}")

        # 2. Insert application profile (NO password column — schema design)
        profile_payload = {
            "id": user_id,
            "email": clean_email,
            "name": name,
            "role": role,
            "license_no": license_no if role == "lawyer" else None,
            "cnic": cnic if role == "lawyer" else None,
            "verification_status": verification_status,
        }
        try:
            client.table("profiles").insert(profile_payload).execute()
            print(f"[Supabase] Profile created for {clean_email} with role '{role}'")
        except Exception as pe:
            print(f"[Supabase Auth] Profile insert note: {pe}")

        # 3. Issue role-enriched JWT
        token = _issue_jwt(user_id, clean_email, name, role)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": clean_email,
                "name": name,
                "role": role,
                "license_no": license_no if role == "lawyer" else None,
                "cnic": cnic if role == "lawyer" else None,
                "verification_status": verification_status,
            },
        }
    except Exception as e:
        print(f"[Supabase Auth] Registration error: {e}")
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a JWT Bearer token and returns the authenticated user profile.
    Supports both internal signed JWTs and Supabase session tokens.
    """
    if not token:
        return None

    clean_token = token.replace("Bearer ", "").replace("bearer ", "").strip()
    if not clean_token:
        return None

    # 1. Try decoding local JWT
    try:
        import jwt
        decoded = jwt.decode(clean_token, JWT_SECRET, algorithms=["HS256"])
        if decoded and "sub" in decoded:
            client = get_supabase_client()
            if client:
                try:
                    prof_res = client.table("profiles").select("*").eq("id", decoded["sub"]).execute()
                    if prof_res.data and len(prof_res.data) > 0:
                        profile = prof_res.data[0]
                        return {
                            "id": profile.get("id"),
                            "email": profile.get("email") or decoded.get("email"),
                            "name": profile.get("name") or decoded.get("name"),
                            "role": profile.get("role") or decoded.get("role", "layman"),
                            "verification_status": profile.get("verification_status", "approved"),
                        }
                except Exception:
                    pass
            return {
                "id": decoded.get("sub"),
                "email": decoded.get("email"),
                "name": decoded.get("name", "User"),
                "role": decoded.get("role", "layman"),
                "verification_status": "approved",
            }
    except Exception:
        pass

    # 2. Try Supabase Auth API
    client = get_supabase_client()
    if not client:
        return None
    try:
        user_res = client.auth.get_user(clean_token)
        if user_res and user_res.user:
            user_id = user_res.user.id
            profile = {}
            try:
                prof_res = client.table("profiles").select("*").eq("id", user_id).execute()
                if prof_res.data and len(prof_res.data) > 0:
                    profile = prof_res.data[0]
            except Exception:
                pass

            return {
                "id": str(user_id),
                "email": user_res.user.email,
                "name": profile.get("name", user_res.user.email.split("@")[0]),
                "role": profile.get("role", "layman"),
                "verification_status": profile.get("verification_status", "not_required"),
            }
        return None
    except Exception as e:
        print(f"[Supabase Auth] Token verification error: {e}")
        return None


def insert_document(
    result_data: Dict[str, Any],
    pdf_url: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    uploaded_by_name: Optional[str] = None,
    uploaded_by_email: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Inserts an extracted judgment into `public.documents` table with full legal data
    and records the uploader in `uploaded_by`.
    """
    client = get_supabase_client()
    if not client:
        print("[Supabase] Client not configured. Skipping database insertion.")
        return None

    metadata = result_data.get("metadata", {}) or {}
    source_file = result_data.get("source_file", "unknown.pdf")

    # Generate clean title
    case_num = metadata.get("case_number")
    parties = metadata.get("parties")
    if case_num and parties:
        title = f"{case_num} - {parties[:60]}"
    elif case_num:
        title = case_num
    elif parties:
        title = parties[:80]
    else:
        title = os.path.splitext(source_file)[0]

    declared_court_type = (
        metadata.get("declared_court_type")
        or metadata.get("court_type_declared")
        or metadata.get("court_type")
        or "SC"
    )
    if declared_court_type not in ("SC", "HC"):
        declared_court_type = "SC" if "supreme" in str(declared_court_type).lower() else "HC"

    # Resolve uploader identity
    uploader_id = uploaded_by

    # Clean metadata dictionary: remove redundant court_type key
    clean_meta = {k: v for k, v in metadata.items() if k != "court_type"}

    doc_payload = {
        "title": title,
        "declared_court_type": declared_court_type,
        "source_file": source_file,
        "pdf_url": pdf_url,
        "total_lines": result_data.get("total_lines", 0),
        "total_chunks": result_data.get("total_chunks", 0),
        "metadata": clean_meta,
        "uploaded_by": uploader_id,
    }

    try:
        response = client.table("documents").insert(doc_payload).execute()
        if response.data and len(response.data) > 0:
            doc = response.data[0]
            print(f"[Supabase] Successfully created document ID: {doc.get('id')} | Uploaded by: {uploader_id}")
            return doc
        return None
    except Exception as e:
        # Auto-adaptive fallback for schema cache ('declared_court_type' vs 'court_type')
        err_str = str(e)
        if "declared_court_type" in err_str or "court_type" in err_str or "PGRST204" in err_str:
            try:
                legacy_payload = dict(doc_payload)
                legacy_payload["court_type"] = declared_court_type
                legacy_payload.pop("declared_court_type", None)
                res = client.table("documents").insert(legacy_payload).execute()
                if res.data and len(res.data) > 0:
                    doc = res.data[0]
                    print(f"[Supabase] Successfully created document ID via column fallback: {doc.get('id')}")
                    return doc
            except Exception as e2:
                print(f"[Supabase] Fallback insert note: {e2}")
        print(f"[Supabase] Error inserting document: {e}")
        return None


def insert_chunks(
    document_id: str,
    chunks: List[Dict[str, Any]],
    source_file: Optional[str] = None,
) -> int:
    """
    Batch inserts chunks into `public.chunks` table with exact bounding boxes.
    `qdrant_point_id` is left NULL for now (will be populated when Qdrant is connected).
    Returns the count of inserted chunks.
    """
    client = get_supabase_client()
    if not client or not document_id or not chunks:
        return 0

    chunk_payloads = []
    for idx, ch in enumerate(chunks):
        chunk_id = ch.get("chunk_id")
        chunk_payloads.append({
            "id": chunk_id,
            "document_id": document_id,
            "chunk_index": idx,
            "text": ch.get("text", ""),
            "word_count": ch.get("word_count", 0),
            "page_start": ch.get("page_start", 1),
            "page_end": ch.get("page_end", 1),
            "bbox": ch.get("bbox", []),
            "qdrant_point_id": None,  # Reserved for Qdrant integration
            "source_file": source_file or ch.get("source_file"),
        })

    try:
        # Batch insert in chunks of 50 to respect Supabase payload limits
        batch_size = 50
        total_inserted = 0
        for i in range(0, len(chunk_payloads), batch_size):
            batch = chunk_payloads[i : i + batch_size]
            res = client.table("chunks").insert(batch).execute()
            if res.data:
                total_inserted += len(res.data)

        print(f"[Supabase] Successfully inserted {total_inserted} chunks for document {document_id}")
        return total_inserted
    except Exception as e:
        print(f"[Supabase] Error inserting chunks: {e}")
        return 0


def save_judgment_to_supabase(
    result_data: Dict[str, Any],
    pdf_url: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    uploaded_by_name: Optional[str] = None,
    uploaded_by_email: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Complete workflow:
    1. Inserts document record into `public.documents`
    2. Inserts all chunks into `public.chunks` linked to document_id
    Returns dict with {"document_id": "...", "chunks_inserted": <int>}
    """
    doc = insert_document(
        result_data,
        pdf_url=pdf_url,
        uploaded_by=uploaded_by,
        uploaded_by_name=uploaded_by_name,
        uploaded_by_email=uploaded_by_email,
    )
    if not doc:
        return None

    doc_id = doc.get("id")
    chunks = result_data.get("chunks", [])
    source_file = result_data.get("source_file")

    total_chunks = insert_chunks(doc_id, chunks, source_file=source_file)

    return {
        "document_id": doc_id,
        "title": doc.get("title"),
        "total_chunks_saved": total_chunks,
    }


def get_database_stats() -> Dict[str, Any]:
    """
    Retrieves live aggregate statistics from Supabase database.
    """
    client = get_supabase_client()
    if not client:
        return {"documents_count": 0, "chunks_count": 0, "recent_documents": []}

    try:
        doc_res = client.table("documents").select("id, title, declared_court_type, created_at, total_chunks, source_file", count="exact").order("created_at", desc=True).limit(5).execute()
        chunk_res = client.table("chunks").select("id", count="exact").limit(1).execute()

        doc_count = doc_res.count if hasattr(doc_res, "count") and doc_res.count is not None else len(doc_res.data or [])
        chunk_count = chunk_res.count if hasattr(chunk_res, "count") and chunk_res.count is not None else 0

        return {
            "documents_count": doc_count,
            "chunks_count": chunk_count,
            "recent_documents": doc_res.data or [],
        }
    except Exception as e:
        print(f"[Supabase] Stats query error: {e}")
        return {"documents_count": 0, "chunks_count": 0, "recent_documents": []}
