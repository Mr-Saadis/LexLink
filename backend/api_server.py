"""
LexLink - Upload API Server
=============================
FastAPI backend handling:
- PDF streaming extraction, chunking, and metadata parsing
- BAAI/bge-m3 dense vector embeddings & Qdrant integration
- Cloudflare R2 original PDF storage
- Supabase persistence (documents & chunks)
- JWT Bearer authentication and Role-Based Access Control (RBAC)
- Live system metrics & stats

Run locally:
    uvicorn api_server:app --reload --port 8000
"""

import os
import shutil
import tempfile
import json
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from judgement_pipeline import process_pdf_stream
from supabase_client import (
    is_supabase_configured,
    save_judgment_to_supabase,
    get_supabase_client,
    get_database_stats,
    authenticate_user,
    register_user,
    get_user_from_token,
)
from r2_client import (
    is_r2_configured,
    upload_file_to_r2,
)
from qdrant_manager import (
    get_qdrant_status,
    upsert_judgment_chunks,
    export_collection_to_json,
    search_similar_chunks,
    get_embedding_dimension,
)

app = FastAPI(title="LexLink Ingestion & Auth API")


# ----------------------------------------------------------------------
# Pydantic Schemas
# ----------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "layman"  # 'layman' | 'lawyer' | 'admin'
    license_no: Optional[str] = None
    cnic: str


class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    declared_court_type: Optional[str] = None
    court_type: Optional[str] = None
    document_id: Optional[str] = None


# ----------------------------------------------------------------------
# CORS Configuration
# ----------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
env_origins = os.getenv("CORS_ORIGINS", "").strip()
if env_origins:
    ALLOWED_ORIGINS = [o.strip() for o in env_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder setup for JSON caching & Qdrant verification JSONs
CHUNK_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chunked_output")
QDRANT_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qdrant_output")
os.makedirs(CHUNK_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(QDRANT_OUTPUT_FOLDER, exist_ok=True)


# ----------------------------------------------------------------------
# System & Health Endpoints
# ----------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    q_status = get_qdrant_status()
    return {
        "status": "online",
        "supabase_connected": is_supabase_configured(),
        "cloudflare_r2_connected": is_r2_configured(),
        "qdrant": q_status,
    }


@app.get("/api/stats")
async def get_system_stats():
    """
    Returns live aggregated statistics from Supabase database, Qdrant vector index, and R2.
    """
    db_stats = get_database_stats()
    q_status = get_qdrant_status()
    return {
        "status": "online",
        "documents_count": db_stats.get("documents_count", 0),
        "chunks_count": db_stats.get("chunks_count", 0),
        "recent_documents": db_stats.get("recent_documents", []),
        "qdrant_points_count": q_status.get("points_count", 0),
        "qdrant_status": q_status.get("status", "unknown"),
        "qdrant_connected": q_status.get("connected", False),
        "supabase_connected": is_supabase_configured(),
        "cloudflare_r2_connected": is_r2_configured(),
        "vector_dimension": q_status.get("vector_dimension", 1024),
        "embedding_model": q_status.get("embedding_model", "BAAI/bge-m3"),
    }


# ----------------------------------------------------------------------
# Qdrant Vector Endpoints
# ----------------------------------------------------------------------
@app.get("/api/qdrant/status")
async def qdrant_status_endpoint(authorization: Optional[str] = Header(None)):
    """Returns current Qdrant connection status, vector dimension, and indexed points count."""
    return get_qdrant_status()


@app.get("/api/qdrant/export")
async def qdrant_export_endpoint(
    include_full_vectors: bool = False,
    limit: int = 500,
    authorization: Optional[str] = Header(None),
):
    """
    Exports current Qdrant collection points as structured JSON for inspection.
    Restricted strictly to administrators.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to export vector data.",
        )
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator privileges required to export Qdrant collection.",
        )

    dump_filename = f"qdrant_dump_{uuid.uuid4().hex[:8]}.json"
    dump_path = os.path.join(QDRANT_OUTPUT_FOLDER, dump_filename)
    data = export_collection_to_json(
        output_path=dump_path,
        limit=limit,
        include_full_vectors=include_full_vectors,
    )
    return data


@app.post("/api/qdrant/search")
async def qdrant_search_endpoint(req: SearchQueryRequest):
    """Executes dense vector semantic search against Qdrant collection using BAAI/bge-m3."""
    court_filter = req.declared_court_type or req.court_type
    results = search_similar_chunks(
        query=req.query,
        top_k=req.top_k,
        court_type=court_filter,
        document_id=req.document_id,
    )
    return {
        "query": req.query,
        "results_count": len(results),
        "results": results,
    }


# ----------------------------------------------------------------------
# Authentication Endpoints
# ----------------------------------------------------------------------
@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    """
    Registers a public user (Layman / Lawyer) in Supabase auth.users & creates public.profiles.
    Admin role cannot be self-assigned via this endpoint.
    """
    # Security: clamp role — public users may only register as layman or lawyer
    safe_role = req.role.lower().strip() if req.role else "layman"
    if safe_role not in ("layman", "lawyer"):
        safe_role = "layman"

    auth_data = register_user(
        email=req.email,
        password=req.password,
        name=req.name,
        role=safe_role,
        license_no=req.license_no,
        cnic=req.cnic,
    )
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Email may already be in use or invalid credentials.",
        )
    return auth_data


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """
    Authenticates user/admin with Supabase Auth and returns JWT token & user profile.
    """
    auth_data = authenticate_user(req.email, req.password)
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return auth_data


@app.get("/api/auth/me")
async def get_current_user_profile(authorization: Optional[str] = Header(None)):
    """
    Validates JWT Bearer token and returns current user info.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired JWT token")
    return {"user": user}


@app.post("/api/auth/admin/create-admin")
async def create_admin_user(
    req: SignupRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Allows an existing Administrator to provision new Administrator accounts.
    Protected strictly by role === 'admin'.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    current_user = get_user_from_token(authorization)
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only existing administrators can create new admin accounts.",
        )

    auth_data = register_user(
        email=req.email,
        password=req.password,
        name=req.name,
        role="admin",
    )
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create admin user. Email may already be registered.",
        )
    return {
        "success": True,
        "message": f"Administrator '{req.email}' created successfully.",
        "user": auth_data.get("user"),
    }


# ----------------------------------------------------------------------
# Document Catalog & Streaming Upload Endpoints
# ----------------------------------------------------------------------
@app.get("/api/documents")
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
):
    """
    Returns recent judgments from database. Requires authenticated session.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view document catalog.",
        )
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session.",
        )

    client = get_supabase_client()
    if not client:
        return {"documents": [], "message": "Supabase not configured"}

    try:
        res = (
            client.table("documents")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"documents": res.data or []}
    except Exception as e:
        return {"error": str(e), "documents": []}


@app.post("/api/upload-judgment")
async def upload_judgment(
    file: UploadFile = File(...),
    dry_run: str = Form(default="true"),
    declared_court_type: Optional[str] = Form(default=None),
    court_type: Optional[str] = Form(default="SC"),
    court_type_declared: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(default=None),
    embed_qdrant: str = Form(default="true"),
):
    """
    Secure document ingestion endpoint.
    Strictly verifies user identity from JWT Bearer token (no user spoofing).
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to upload documents.",
        )

    user_info = get_user_from_token(authorization)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please sign in again.",
        )

    user_id = user_info.get("id")
    user_name = user_info.get("name")
    user_email = user_info.get("email")
    print(f"[Upload Auth] Authenticated user from JWT: {user_name} ({user_email}) | ID: {user_id}")

    # Determine declared court type (defaults to "SC" if unspecified)
    declared_type = declared_court_type or court_type_declared or court_type or "SC"
    declared_type = declared_type.strip().upper()
    if declared_type not in ("SC", "HC"):
        declared_type = "SC" if "supreme" in declared_type.lower() else "HC"

    orig_filename = file.filename or "uploaded.pdf"
    suffix = os.path.splitext(orig_filename)[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    def event_generator():
        try:
            for event in process_pdf_stream(tmp_path, declared_court_type=declared_type):
                if event["type"] == "error":
                    yield json.dumps({"success": False, "detail": event["detail"]}) + "\n"
                    return

                if event["type"] == "progress":
                    yield json.dumps({
                        "type": "progress",
                        "stage_index": event["stage_index"],
                        "stage_name": event["stage_name"],
                    }) + "\n"
                    continue

                if event["type"] == "result":
                    result = event["data"]
                    result["source_file"] = orig_filename

                    # 1. Save standard chunked JSON to disk
                    out_name = f"{uuid.uuid4()}.json"
                    out_path = os.path.join(CHUNK_OUTPUT_FOLDER, out_name)
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)

                    db_result = None
                    doc_id = None
                    r2_pdf_url = None

                    if dry_run.lower() != "true":
                        # 2. Upload original PDF to Cloudflare R2 if configured
                        if is_r2_configured():
                            object_key = f"judgments/{uuid.uuid4()}_{orig_filename}"
                            print(f"[Upload] Uploading PDF '{orig_filename}' to Cloudflare R2: {object_key}...")
                            r2_pdf_url = upload_file_to_r2(tmp_path, object_key, content_type="application/pdf")
                            print(f"[Upload] Cloudflare R2 URL generated: {r2_pdf_url}")
                        else:
                            print("[Upload] Cloudflare R2 is not configured. Skipping R2 upload.")

                        # 3. Persist to Supabase Database (uploaded_by strictly linked to JWT user)
                        if is_supabase_configured():
                            print(f"[Upload] Persisting judgment '{orig_filename}' to Supabase for user {user_id}...")
                            db_result = save_judgment_to_supabase(
                                result_data=result,
                                pdf_url=r2_pdf_url,
                                uploaded_by=user_id,
                                uploaded_by_name=user_name,
                                uploaded_by_email=user_email,
                            )
                            if db_result:
                                doc_id = db_result.get("document_id")
                    else:
                        print("[Upload] Dry run mode active: skipping R2 and DB persistence.")

                    # 4. Qdrant Vector Embedding & Verification JSON Generation
                    qdrant_res = None
                    if embed_qdrant.lower() != "false" and result.get("chunks"):
                        try:
                            qdrant_res = upsert_judgment_chunks(
                                result_data=result,
                                document_id=doc_id,
                                save_json_file=True,
                                output_dir=QDRANT_OUTPUT_FOLDER,
                                include_full_vectors_in_json=True,
                            )
                        except Exception as q_err:
                            print(f"[Qdrant Embedding Error]: {q_err}")
                            qdrant_res = {"success": False, "error": str(q_err)}

                    final_payload = {
                        "type": "final",
                        "success": True,
                        "metadata": result["metadata"],
                        "total_chunks": result["total_chunks"],
                        "total_lines": result["total_lines"],
                        "boilerplate_removed_count": len(result["boilerplate_removed"]),
                        "source_file": orig_filename,
                        "json_saved_to": out_path,
                        "pdf_url": r2_pdf_url,
                        "db_persisted": bool(db_result),
                        "document_id": doc_id,
                        "chunks_saved": db_result.get("total_chunks_saved") if db_result else 0,
                        "qdrant_embedded": bool(qdrant_res and qdrant_res.get("success")),
                        "qdrant_points_count": qdrant_res.get("points_upserted", 0) if qdrant_res else 0,
                        "qdrant_mode": qdrant_res.get("qdrant_mode") if qdrant_res else None,
                        "qdrant_json_saved_to": qdrant_res.get("qdrant_json_path") if qdrant_res else None,
                        "vector_dimension": qdrant_res.get("vector_dimension", get_embedding_dimension()) if qdrant_res else None,
                        "embedding_model": qdrant_res.get("embedding_model") if qdrant_res else None,
                    }
                    yield json.dumps(final_payload) + "\n"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)