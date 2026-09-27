from fastapi import APIRouter
from services.health_service import get_health_status

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health_check():
    """Returns overall health and connectivity status of backing services."""
    return get_health_status()
