from typing import Optional
from pydantic import BaseModel

class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    court_type: Optional[str] = None
    document_id: Optional[str] = None
