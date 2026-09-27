from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BatchConfig(BaseModel):
    input_path: str = "supreme_court_judgments"
    output_folder: str = "chunked_output"
    qdrant_output_folder: Optional[str] = None
    court_type: Optional[str] = None
    embed: bool = True
    sync_db: bool = False
    sync_r2: bool = False
    limit: Optional[int] = None
    workers: int = 1
    resume: bool = True
    engine: str = "celery"  # "celery" | "local"


class BatchFileResult(BaseModel):
    file: str
    status: str  # "success" | "skipped" | "failed"
    chunks: int = 0
    judge: Optional[str] = None
    case_number: Optional[str] = None
    qdrant_embedded: bool = False
    qdrant_points: int = 0
    qdrant_json: Optional[str] = None
    db_persisted: bool = False
    r2_url: Optional[str] = None
    reason: Optional[str] = None


class BatchSummary(BaseModel):
    total_found: int = 0
    total_processed: int = 0
    successful: int = 0
    skipped_unreadable: List[Dict[str, Any]] = Field(default_factory=list)
    skipped_already_done: int = 0
    failed: List[Dict[str, Any]] = Field(default_factory=list)
    total_qdrant_points: int = 0
    elapsed_seconds: float = 0.0
    log_path: Optional[str] = None
    engine_used: Optional[str] = None
