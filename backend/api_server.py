"""
LexLink - Ingestion & Auth API Server
=====================================
Main application entrypoint configuring FastAPI, CORS middleware,
and endpoint routers.

Run with:
    uvicorn api_server:app --reload --port 8000
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import api_router

# Ensure runtime cache/output folders exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNK_OUTPUT_FOLDER = os.path.join(BASE_DIR, "chunked_output")
QDRANT_OUTPUT_FOLDER = os.path.join(BASE_DIR, "qdrant_output")
os.makedirs(CHUNK_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(QDRANT_OUTPUT_FOLDER, exist_ok=True)

# Initialize FastAPI application
app = FastAPI(
    title="LexLink Ingestion & Auth API",
    description="Backend API for LexLink legal intelligence platform, authentication, document processing, and vector search.",
    version="1.0.0",
)

# CORS middleware configuration for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)