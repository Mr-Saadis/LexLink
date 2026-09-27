import os
import uuid
from typing import Optional, Dict, Any
from models.search import SearchQueryRequest
from qdrant_manager import (
    get_qdrant_status,
    export_collection_to_json,
    search_similar_chunks,
)


def get_status() -> Dict[str, Any]:
    """
    Returns current Qdrant connection status, vector dimension, and indexed points count.
    """
    return get_qdrant_status()


def export_collection(output_folder: str, include_full_vectors: bool = False, limit: int = 500) -> Dict[str, Any]:
    """
    Exports and returns current Qdrant collection points as structured JSON for inspection.
    """
    dump_filename = f"qdrant_dump_{uuid.uuid4().hex[:8]}.json"
    dump_path = os.path.join(output_folder, dump_filename)
    data = export_collection_to_json(
        output_path=dump_path,
        limit=limit,
        include_full_vectors=include_full_vectors,
    )
    return data


def search_chunks(req: SearchQueryRequest) -> Dict[str, Any]:
    """
    Executes dense vector semantic search against Qdrant collection using BAAI/bge-m3.
    """
    results = search_similar_chunks(
        query=req.query,
        top_k=req.top_k,
        court_type=req.court_type,
        document_id=req.document_id,
    )
    return {
        "query": req.query,
        "results_count": len(results),
        "results": results,
    }
