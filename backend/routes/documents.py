from fastapi import APIRouter
from services.document_service import list_documents

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("")
@router.get("/")
async def get_documents_endpoint(limit: int = 50, offset: int = 0):
    """
    Fetches paginated list of ingested documents/judgments.
    """
    return list_documents(limit=limit, offset=offset)
