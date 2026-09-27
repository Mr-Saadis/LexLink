import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from services.upload_service import process_judgment_upload

router = APIRouter(tags=["Upload"])


@router.post("/api/upload-judgment")
async def upload_judgment_endpoint(
    file: UploadFile = File(...),
    dry_run: str = Form(default="true"),
    court_type: str = Form(default="SC"),
    court_type_declared: Optional[str] = Form(default=None),
    uploaded_by: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(default=None),
    embed_qdrant: str = Form(default="true"),
):
    """
    Uploads, streams processing events, stores original PDF to Cloudflare R2,
    persists metadata and chunks to Supabase, and embeds vectors into Qdrant.
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chunk_folder = os.path.join(backend_dir, "chunked_output")
    qdrant_folder = os.path.join(backend_dir, "qdrant_output")

    generator = process_judgment_upload(
        file_obj=file.file,
        filename=file.filename,
        dry_run=dry_run,
        court_type=court_type,
        court_type_declared=court_type_declared,
        uploaded_by=uploaded_by,
        authorization=authorization,
        embed_qdrant=embed_qdrant,
        chunk_output_folder=chunk_folder,
        qdrant_output_folder=qdrant_folder,
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")
