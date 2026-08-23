"""
LexLink - Upload API Server
=============================
Yeh wo backend hai jise tumhara React component (DocumentIngestion.tsx)
already call kar raha hai:

    fetch("http://localhost:8000/api/upload-judgment", {
        method: "POST",
        body: formData,   // fields: file, dry_run
    })

"Select Files" click karne pe -> handleFilesSelected -> processFileIngestion
-> yeh endpoint hit hota hai -> judgement_pipeline.process_pdf_stream()
STREAM hota hai (parsing -> extracting -> verifying -> final), taake
frontend har stage pe UI update kar sake -> full chunked result JSON
disk pe save hota hai (CHUNK_OUTPUT_FOLDER me) -> aakhri "final" event
frontend ko milta hai jahan se data.metadata.case_number queue card pe
dikhaya jata hai.

Run karne ke liye:
    pip install fastapi uvicorn python-multipart pymupdf
    python3 api_server.py
    # ya: uvicorn api_server:app --reload --port 8000
"""

import os
import shutil
import tempfile
import json
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from judgement_pipeline import process_pdf_stream
from supabase_client import (
    is_supabase_configured,
    save_judgment_to_supabase,
    get_supabase_client,
)

app = FastAPI(title="LexLink Ingestion API")

# Dev ke liye CORS open rakha hai (frontend Vite/CRA dev server alag port
# pe chalta hai, e.g. localhost:5173, jab backend localhost:8000 pe hai).
# Production me isko apne actual frontend domain tak restrict karna.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Har upload ka chunked JSON yahan save hoga (backend folder ke andar,
# api_server.py ke sath hi). Folder khud-b-khud ban jayega agar exist
# nahi karta.
CHUNK_OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chunked_output")
os.makedirs(CHUNK_OUTPUT_FOLDER, exist_ok=True)


@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "supabase_connected": is_supabase_configured(),
    }


@app.get("/api/documents")
async def list_documents(limit: int = 50, offset: int = 0):
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
    court_type: str = Form(default="SC"),
    court_type_declared: str = Form(default=None),
    uploaded_by: str = Form(default=None),
):
    # Determine declared court type (defaults to "SC" if unspecified)
    declared_type = court_type_declared or court_type or "SC"
    declared_type = declared_type.strip().upper()
    if declared_type not in ("SC", "HC"):
        declared_type = "SC" if "supreme" in declared_type.lower() else "HC"

    # Uploaded file ko disk pe temp location par save karna zaroori hai
    # kyunke PyMuPDF (fitz) file PATH se open karta hai, in-memory bytes
    # se seedha nahi.
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

                    # Save JSON to disk for caching & verification
                    out_name = f"{uuid.uuid4()}.json"
                    out_path = os.path.join(CHUNK_OUTPUT_FOLDER, out_name)
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)

                    # If dry_run is false AND Supabase credentials exist, persist to database
                    db_result = None
                    if dry_run.lower() != "true" and is_supabase_configured():
                        db_result = save_judgment_to_supabase(
                            result_data=result,
                            uploaded_by=uploaded_by,
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
                        "db_persisted": bool(db_result),
                        "document_id": db_result.get("document_id") if db_result else None,
                        "chunks_saved": db_result.get("total_chunks_saved") if db_result else 0,
                    }
                    yield json.dumps(final_payload) + "\n"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)