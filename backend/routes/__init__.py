from fastapi import APIRouter
from .health import router as health_router
from .auth import router as auth_router
from .documents import router as documents_router
from .qdrant import router as qdrant_router
from .upload import router as upload_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(qdrant_router)
api_router.include_router(upload_router)

__all__ = ["api_router"]
