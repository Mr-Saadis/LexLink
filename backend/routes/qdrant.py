import os
from fastapi import APIRouter
from models.search import SearchQueryRequest
from services.qdrant_service import get_status, export_collection, search_chunks

router = APIRouter(prefix="/api/qdrant", tags=["Qdrant"])


@router.get("/status")
async def qdrant_status_endpoint():
    """Returns current Qdrant connection status, vector dimension, and indexed points count."""
    return get_status()


@router.get("/export")
async def qdrant_export_endpoint(include_full_vectors: bool = False, limit: int = 500):
    """Exports and returns current Qdrant collection points as structured JSON for inspection."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_folder = os.path.join(backend_dir, "qdrant_output")
    return export_collection(
        output_folder=output_folder,
        include_full_vectors=include_full_vectors,
        limit=limit,
    )


@router.post("/search")
async def qdrant_search_endpoint(req: SearchQueryRequest):
    """Executes dense vector semantic search against Qdrant collection using BAAI/bge-m3."""
    return search_chunks(req)
