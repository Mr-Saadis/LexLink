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


def insert_document(
    result_data: Dict[str, Any],
    pdf_url: Optional[str] = None,
    uploaded_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Inserts an extracted judgment into `public.documents` table.
    Returns the created document record (including 'id').
    """
    client = get_supabase_client()
    if not client:
        print("[Supabase] Client not configured. Skipping database insertion.")
        return None

    metadata = result_data.get("metadata", {}) or {}
    source_file = result_data.get("source_file", "unknown.pdf")

    # Generate a clean title
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

    court_type = metadata.get("court_type") or metadata.get("court_type_declared") or "SC"
    court_type_declared = metadata.get("court_type_declared") or court_type

    doc_payload = {
        "title": title,
        "court": metadata.get("court"),
        "court_type": court_type,
        "court_type_declared": court_type_declared,
        "case_number": metadata.get("case_number"),
        "parties": metadata.get("parties"),
        "judge": metadata.get("judge"),
        "judgment_date": metadata.get("date"),
        "dates_of_hearing": metadata.get("dates_of_hearing"),
        "source_file": source_file,
        "pdf_url": pdf_url,
        "total_lines": result_data.get("total_lines", 0),
        "total_chunks": result_data.get("total_chunks", 0),
        "metadata": metadata,
        "uploaded_by": uploaded_by,
    }

    try:
        response = client.table("documents").insert(doc_payload).execute()
        if response.data and len(response.data) > 0:
            doc = response.data[0]
            print(f"[Supabase] Successfully created document ID: {doc.get('id')}")
            return doc
        return None
    except Exception as e:
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
) -> Optional[Dict[str, Any]]:
    """
    Complete workflow:
    1. Inserts document record into `public.documents`
    2. Inserts all chunks into `public.chunks` linked to document_id
    Returns dict with {"document_id": "...", "chunks_inserted": <int>}
    """
    doc = insert_document(result_data, pdf_url=pdf_url, uploaded_by=uploaded_by)
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
