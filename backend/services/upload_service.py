import os
import shutil
import tempfile
import json
import uuid
from typing import Optional, Generator, BinaryIO

from judgement_pipeline import process_pdf_stream
from supabase_client import (
    is_supabase_configured,
    save_judgment_to_supabase,
    get_user_from_token,
)
from r2_client import (
    is_r2_configured,
    upload_file_to_r2,
)
from qdrant_manager import (
    upsert_judgment_chunks,
    get_embedding_dimension,
)


def process_judgment_upload(
    file_obj: BinaryIO,
    filename: str,
    dry_run: str = "true",
    court_type: str = "SC",
    court_type_declared: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    authorization: Optional[str] = None,
    embed_qdrant: str = "true",
    chunk_output_folder: str = "chunked_output",
    qdrant_output_folder: str = "qdrant_output",
) -> Generator[str, None, None]:
    """
    Handles PDF ingestion pipeline stream, Cloudflare R2 upload,
    Supabase DB persistence, and Qdrant vector indexing.
    Yields NDJSON formatted progress and result events.
    """
    # Determine user ID: check uploaded_by form field or decode from JWT Authorization header
    user_id = uploaded_by
    user_name = None
    user_email = None
    if not user_id and authorization:
        user_info = get_user_from_token(authorization)
        if user_info:
            user_id = user_info.get("id")
            user_name = user_info.get("name")
            user_email = user_info.get("email")
            print(f"[Upload Auth] Authenticated user from JWT: {user_name} ({user_email})")
    elif user_id and authorization:
        # uploaded_by passed directly, still try to get name/email from token
        user_info = get_user_from_token(authorization)
        if user_info:
            user_name = user_info.get("name")
            user_email = user_info.get("email")

    # Determine declared court type (defaults to "SC" if unspecified)
    declared_type = court_type_declared or court_type or "SC"
    declared_type = declared_type.strip().upper()
    if declared_type not in ("SC", "HC"):
        declared_type = "SC" if "supreme" in declared_type.lower() else "HC"

    orig_filename = filename or "uploaded.pdf"
    suffix = os.path.splitext(orig_filename)[1] or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file_obj, tmp)
        tmp_path = tmp.name

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
                out_path = os.path.join(chunk_output_folder, out_name)
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

                    # 3. Persist to Supabase Database
                    if is_supabase_configured():
                        print(f"[Upload] Persisting judgment '{orig_filename}' to Supabase...")
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
                    qdrant_res = upsert_judgment_chunks(
                        result_data=result,
                        document_id=doc_id,
                        save_json_file=True,
                        output_dir=qdrant_output_folder,
                        include_full_vectors_in_json=True,
                    )

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
