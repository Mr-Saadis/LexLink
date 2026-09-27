# backend/qdrant_manager.py
"""
LexLink - Qdrant Vector Database & BAAI/bge-m3 Embedding Engine
==============================================================
Handles:
1. SentenceTransformer embedding generation (BAAI/bge-m3 with 1024-dim dense vectors).
2. Dual-mode Qdrant connection:
   - Remote/Docker server (http://localhost:6333 or cloud URL via QDRANT_URL)
   - Embedded local disk fallback (backend/qdrant_storage) for friction-free local dev.
3. Collection management (lexlink_judgments with Cosine distance & payload indexing).
4. Chunk vector indexing & metadata payload storage.
5. Structured Qdrant Verification JSON generation for direct human & pipeline inspection.
6. Semantic vector similarity search with Top-K and metadata filtering.
"""

import os
import json
import uuid
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv
import numpy as np

# Load .env file from the current directory or backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
DEFAULT_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL_NAME).strip()

QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip() or None
DEFAULT_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qdrant_storage")
QDRANT_STORAGE_PATH = os.getenv("QDRANT_PATH", DEFAULT_STORAGE_DIR)

DEFAULT_COLLECTION = "lexlink_judgments"
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION).strip()

DEFAULT_QDRANT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qdrant_output")
QDRANT_OUTPUT_DIR = os.getenv("QDRANT_OUTPUT_DIR", DEFAULT_QDRANT_OUTPUT_DIR)

# Singletons
_model_instance = None
_qdrant_client_instance = None
_qdrant_client_mode = None  # "remote" or "embedded_disk"


# ----------------------------------------------------------------------
# 1. EMBEDDING ENGINE (SentenceTransformer / BAAI/bge-m3)
# ----------------------------------------------------------------------
def get_embedding_model():
    """
    Returns the singleton SentenceTransformer instance.
    Lazy-loads on first call.
    """
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    from sentence_transformers import SentenceTransformer

    print(f"[EmbeddingEngine] Loading model '{EMBEDDING_MODEL_NAME}'...")
    _model_instance = SentenceTransformer(EMBEDDING_MODEL_NAME)
    dim = _model_instance.get_sentence_embedding_dimension()
    print(f"[EmbeddingEngine] Model '{EMBEDDING_MODEL_NAME}' loaded successfully (dimension={dim}).")
    return _model_instance


def get_embedding_dimension() -> int:
    """Returns the embedding vector dimension for the active model."""
    try:
        model = get_embedding_model()
        return model.get_sentence_embedding_dimension()
    except Exception:
        return 1024  # Default for BAAI/bge-m3


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Computes normalized dense embeddings for a list of strings.
    Returns list of float vectors.
    """
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 10,
        normalize_embeddings=True,
    )

    if isinstance(embeddings, np.ndarray):
        return embeddings.tolist()
    return [list(vec) for vec in embeddings]


# ----------------------------------------------------------------------
# 2. QDRANT CLIENT CONNECTION (Dual-Mode: Remote vs Embedded Disk)
# ----------------------------------------------------------------------
def get_qdrant_client() -> Tuple[Any, str]:
    """
    Returns (client, mode) where mode is 'remote' or 'embedded_disk'.
    Automatically attempts remote Qdrant if QDRANT_URL is set;
    otherwise falls back to embedded local disk storage.
    """
    global _qdrant_client_instance, _qdrant_client_mode
    if _qdrant_client_instance is not None:
        return _qdrant_client_instance, _qdrant_client_mode

    from qdrant_client import QdrantClient

    # Attempt Remote Connection if QDRANT_URL is configured
    if QDRANT_URL and "localhost" not in QDRANT_URL or (QDRANT_URL and _check_url_available(QDRANT_URL)):
        try:
            print(f"[Qdrant] Connecting to remote cluster at {QDRANT_URL}...")
            client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                timeout=15.0,
                check_compatibility=False,
            )
            # Test connectivity
            client.get_collections()
            _qdrant_client_instance = client
            _qdrant_client_mode = "remote"
            print(f"[Qdrant] Connected to remote Qdrant cluster successfully.")
            return _qdrant_client_instance, _qdrant_client_mode
        except Exception as e:
            print(f"[Qdrant] Remote connection failed ({e}). Falling back to local disk...")

    # Embedded Disk Fallback
    os.makedirs(QDRANT_STORAGE_PATH, exist_ok=True)
    print(f"[Qdrant] Initializing local embedded storage at '{QDRANT_STORAGE_PATH}'...")
    client = QdrantClient(path=QDRANT_STORAGE_PATH)
    _qdrant_client_instance = client
    _qdrant_client_mode = "embedded_disk"
    print(f"[Qdrant] Local embedded Qdrant initialized successfully.")
    return _qdrant_client_instance, _qdrant_client_mode


def _check_url_available(url: str, timeout: float = 1.0) -> bool:
    """Quick check if a remote HTTP URL is reachable."""
    import urllib.request
    try:
        req = urllib.request.Request(url.rstrip("/") + "/collections", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 401, 403)
    except Exception:
        return False


def get_qdrant_status() -> Dict[str, Any]:
    """Returns connectivity and collection statistics for health checks."""
    try:
        client, mode = get_qdrant_client()
        collections_resp = client.get_collections()
        col_names = [c.name for c in collections_resp.collections]

        point_count = 0
        vector_size = None
        if COLLECTION_NAME in col_names:
            info = client.get_collection(COLLECTION_NAME)
            point_count = info.points_count or 0
            if hasattr(info.config.params, "vectors"):
                vconfig = info.config.params.vectors
                vector_size = getattr(vconfig, "size", None)

        return {
            "status": "online",
            "mode": mode,
            "url": QDRANT_URL if mode == "remote" else QDRANT_STORAGE_PATH,
            "collection_name": COLLECTION_NAME,
            "collection_exists": COLLECTION_NAME in col_names,
            "points_count": point_count,
            "vector_dimension": vector_size or get_embedding_dimension(),
            "embedding_model": EMBEDDING_MODEL_NAME,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "mode": "disconnected",
            "embedding_model": EMBEDDING_MODEL_NAME,
        }


# ----------------------------------------------------------------------
# 3. COLLECTION SETUP & INDEXING
# ----------------------------------------------------------------------
def ensure_collection(
    collection_name: str = COLLECTION_NAME,
    vector_dim: Optional[int] = None,
) -> bool:
    """
    Ensures the target Qdrant collection exists with the required vector dimension
    and cosine distance metric, creating fast payload indexes for filtering.
    """
    from qdrant_client.http import models

    client, mode = get_qdrant_client()
    dim = vector_dim or get_embedding_dimension()

    try:
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            print(f"[Qdrant] Creating collection '{collection_name}' (dim={dim}, metric=Cosine)...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dim,
                    distance=models.Distance.COSINE,
                ),
            )
            print(f"[Qdrant] Collection '{collection_name}' created.")

        # Create payload indexes for instant metadata filtering
        _create_payload_indexes(client, collection_name)
        return True
    except Exception as e:
        print(f"[Qdrant] Error ensuring collection '{collection_name}': {e}")
        return False


def _create_payload_indexes(client: Any, collection_name: str):
    """Creates payload indexes for fast filtered vector searches if needed."""
    from qdrant_client.http import models

    index_fields = [
        ("chunk_id", models.PayloadSchemaType.KEYWORD),
    ]

    for field_name, field_schema in index_fields:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )
        except Exception:
            # Index already exists or not supported in local mode - safe to ignore
            pass


# ----------------------------------------------------------------------
# 4. CHUNK EMBEDDING & UPSERTION
# ----------------------------------------------------------------------
def upsert_judgment_chunks(
    result_data: Dict[str, Any],
    document_id: Optional[str] = None,
    collection_name: str = COLLECTION_NAME,
    save_json_file: bool = True,
    output_dir: Optional[str] = None,
    include_full_vectors_in_json: bool = True,
) -> Dict[str, Any]:
    """
    Complete embedding & Qdrant upsert pipeline for an extracted judgment:
    1. Embeds all chunk texts using BAAI/bge-m3.
    2. Builds PointStruct records with clean, minimal payloads (chunk_id, chunk_index, word_count, text, embedded_at).
    3. Upserts points into Qdrant collection.
    4. Generates a structured Qdrant verification JSON file on disk.

    Returns:
        {
            "success": bool,
            "collection_name": str,
            "points_upserted": int,
            "vector_dimension": int,
            "embedding_model": str,
            "qdrant_json_path": str,
            "points": List[Dict],  # Point records with payloads & vector previews
        }
    """
    from qdrant_client.http import models

    chunks = result_data.get("chunks", [])
    if not chunks:
        return {
            "success": False,
            "error": "No chunks found in result_data to embed",
            "points_upserted": 0,
        }

    # Ensure collection exists
    vector_dim = get_embedding_dimension()
    ensure_collection(collection_name=collection_name, vector_dim=vector_dim)

    source_file = result_data.get("source_file", "unknown.pdf")

    # 1. Generate embeddings in batch
    texts = [ch.get("text", "") for ch in chunks]
    print(f"[Qdrant] Embedding {len(texts)} chunk(s) using {EMBEDDING_MODEL_NAME}...")
    vectors = embed_texts(texts, batch_size=32)

    # 2. Build PointStruct list and JSON export structure
    points_to_upsert = []
    points_export_list = []
    timestamp = datetime.utcnow().isoformat() + "Z"

    for idx, (ch, vec) in enumerate(zip(chunks, vectors)):
        chunk_id = ch.get("chunk_id") or str(uuid.uuid4())
        ch["chunk_id"] = chunk_id

        # Clean streamlined payload with chunk attributes and embedding vector
        payload = {
            "chunk_id": chunk_id,
            "chunk_index": idx,
            "word_count": ch.get("word_count", len(ch.get("text", "").split())),
            "text": ch.get("text", ""),
            "text_embeddings": vec,
            "embedded_at": timestamp,
        }

        points_to_upsert.append(
            models.PointStruct(
                id=chunk_id,
                vector=vec,
                payload=payload,
            )
        )

        # Build point dictionary for JSON verification output
        norm = math.sqrt(sum(v * v for v in vec)) if vec else 0.0
        point_record = {
            "point_id": chunk_id,
            "chunk_index": idx,
            "payload": payload,
            "vector_dimension": len(vec),
            "vector_l2_norm": round(norm, 4),
            "vector_preview": {
                "first_5_values": [round(v, 6) for v in vec[:5]],
                "last_5_values": [round(v, 6) for v in vec[-5:]],
            },
        }
        if include_full_vectors_in_json:
            point_record["vector"] = vec

        points_export_list.append(point_record)

    # 3. Upsert to Qdrant in batches of 64
    client, mode = get_qdrant_client()
    batch_size = 64
    for i in range(0, len(points_to_upsert), batch_size):
        batch = points_to_upsert[i : i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch,
        )

    print(f"[Qdrant] Successfully upserted {len(points_to_upsert)} point(s) into collection '{collection_name}' (mode: {mode}).")

    # 4. Generate structured Qdrant verification JSON
    json_path = None
    export_payload = {
        "export_type": "lexlink_qdrant_verification",
        "generated_at": timestamp,
        "collection_name": collection_name,
        "qdrant_mode": mode,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "vector_dimension": vector_dim,
        "distance_metric": "Cosine",
        "source_file": source_file,
        "total_chunks_embedded": len(points_export_list),
        "points": points_export_list,
    }

    if save_json_file:
        out_dir = output_dir or QDRANT_OUTPUT_DIR
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        json_filename = f"{base_name}_qdrant.json"
        json_path = os.path.join(out_dir, json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, ensure_ascii=False, indent=2)
        print(f"[Qdrant] Verification JSON saved to: {json_path}")

    return {
        "success": True,
        "collection_name": collection_name,
        "points_upserted": len(points_to_upsert),
        "vector_dimension": vector_dim,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "qdrant_mode": mode,
        "qdrant_json_path": json_path,
        "points": points_export_list,
    }


# ----------------------------------------------------------------------
# 5. QDRANT COLLECTION EXPORT & AUDIT UTILITIES
# ----------------------------------------------------------------------
def export_collection_to_json(
    output_path: str,
    collection_name: str = COLLECTION_NAME,
    limit: int = 500,
    include_full_vectors: bool = False,
) -> Dict[str, Any]:
    """
    Scrolls points from Qdrant and saves a full collection export JSON.
    Useful for auditing all indexed judgments and vector payloads.
    """
    client, mode = get_qdrant_client()
    ensure_collection(collection_name)

    records, next_page = client.scroll(
        collection_name=collection_name,
        limit=limit,
        with_payload=True,
        with_vectors=True,
    )

    points_data = []
    for r in records:
        vec = r.vector if isinstance(r.vector, list) else []
        norm = math.sqrt(sum(v * v for v in vec)) if vec else 0.0
        pt = {
            "point_id": str(r.id),
            "payload": r.payload,
            "vector_dimension": len(vec),
            "vector_l2_norm": round(norm, 4),
            "vector_preview": {
                "first_5_values": [round(v, 6) for v in vec[:5]],
                "last_5_values": [round(v, 6) for v in vec[-5:]],
            } if vec else None,
        }
        if include_full_vectors and vec:
            pt["vector"] = vec
        points_data.append(pt)

    export_obj = {
        "export_type": "lexlink_qdrant_collection_dump",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "collection_name": collection_name,
        "qdrant_mode": mode,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "vector_dimension": get_embedding_dimension(),
        "total_points_exported": len(points_data),
        "points": points_data,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_obj, f, ensure_ascii=False, indent=2)

    print(f"[Qdrant] Collection exported ({len(points_data)} points) to: {output_path}")
    return export_obj


def strip_deprecated_payload_attributes(
    collection_name: str = COLLECTION_NAME,
    attributes_to_remove: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Scrolls across all existing points in the Qdrant collection and deletes
    the deprecated/removed metadata attributes from every point payload.
    """
    client, mode = get_qdrant_client()
    ensure_collection(collection_name)

    keys = attributes_to_remove or [
        "source_file", "case_number", "court", "court_type", "court_type_declared",
        "parties", "judge", "judgment_date", "dates_of_hearing", "year",
        "bbox", "page_start", "page_end", "document_id"
    ]

    offset = None
    all_point_ids = []
    while True:
        records, offset = client.scroll(
            collection_name=collection_name,
            limit=200,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        for r in records:
            all_point_ids.append(r.id)
        if offset is None:
            break

    print(f"[Qdrant] Stripping deprecated attributes from {len(all_point_ids)} points in '{collection_name}'...")
    batch_size = 100
    for i in range(0, len(all_point_ids), batch_size):
        batch = all_point_ids[i : i + batch_size]
        client.delete_payload(
            collection_name=collection_name,
            keys=keys,
            points=batch,
        )

    print(f"[Qdrant] Successfully cleaned {len(all_point_ids)} point payloads.")
    return {
        "success": True,
        "collection_name": collection_name,
        "points_cleaned": len(all_point_ids),
        "removed_keys": keys,
    }


# ----------------------------------------------------------------------
# 6. SEMANTIC VECTOR SEARCH (Cosine Similarity Top-K)
# ----------------------------------------------------------------------
def search_similar_chunks(
    query: str,
    top_k: int = 5,
    collection_name: str = COLLECTION_NAME,
    include_embeddings: bool = False,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Executes dense vector semantic search over embedded legal chunks.
    """
    client, mode = get_qdrant_client()
    ensure_collection(collection_name)

    # 1. Embed query
    query_vectors = embed_texts([query], batch_size=1)
    if not query_vectors:
        return []
    query_vector = query_vectors[0]

    # 2. Execute search using modern query_points
    if hasattr(client, "query_points"):
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        hits = results.points
    else:
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    formatted_results = []
    for hit in hits:
        payload = hit.payload or {}
        res_item = {
            "chunk_id": str(hit.id),
            "score": round(float(hit.score), 4),
            "chunk_index": payload.get("chunk_index"),
            "word_count": payload.get("word_count"),
            "text": payload.get("text"),
            "embedded_at": payload.get("embedded_at"),
        }
        if include_embeddings:
            res_item["text_embeddings"] = payload.get("text_embeddings")
        formatted_results.append(res_item)

    return formatted_results


# ----------------------------------------------------------------------
# CLI ENTRY POINT (For testing & inspection from terminal)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LexLink Qdrant & Embedding Manager")
    parser.add_argument("--status", action="store_true", help="Check Qdrant & model status")
    parser.add_argument("--export", type=str, default=None, help="Export Qdrant collection to JSON file")
    parser.add_argument("--search", type=str, default=None, help="Run a test vector search query")
    parser.add_argument("--top-k", type=int, default=3, help="Number of search results to return")
    parser.add_argument("--clean-payloads", action="store_true", help="Strip deprecated attributes from all collection points in Qdrant")
    args = parser.parse_args()

    if args.status:
        st = get_qdrant_status()
        print("\n" + "=" * 60)
        print("LEXLINK QDRANT & EMBEDDING STATUS")
        print("=" * 60)
        for k, v in st.items():
            print(f"  {k:20}: {v}")
        print("=" * 60)

    elif args.clean_payloads:
        res = strip_deprecated_payload_attributes()
        print(f"\n[Qdrant] Cleaned {res['points_cleaned']} points in collection '{res['collection_name']}'.")

    elif args.export:
        export_collection_to_json(args.export, include_full_vectors=False)

    elif args.search:
        print(f"\nSearching for: '{args.search}' (top_k={args.top_k})...\n")
        results = search_similar_chunks(args.search, top_k=args.top_k)
        for i, res in enumerate(results, 1):
            print(f"[{i}] Score: {res['score']:.4f} | Chunk Index: {res.get('chunk_index')} | Word Count: {res.get('word_count')}")
            print(f"    Chunk ID: {res['chunk_id']}")
            text_preview = (res.get("text") or "")[:120].replace("\n", " ")
            print(f"    Text: {text_preview}...\n")
    else:
        st = get_qdrant_status()
        print(f"Qdrant Status: {st['status']} (mode: {st.get('mode')}, collection: {st.get('collection_name')})")
        print("Use --help for available CLI options.")