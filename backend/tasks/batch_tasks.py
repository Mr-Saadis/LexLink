import os
from typing import Dict, Any, Optional
from celery_app import celery_app


@celery_app.task(bind=True, name="process_pdf_judgment_task")
def process_pdf_judgment_task(
    self,
    pdf_path: str,
    output_folder: str,
    qdrant_output_folder: str,
    court_type: Optional[str] = None,
    embed: bool = True,
    sync_db: bool = False,
    sync_r2: bool = False,
) -> Dict[str, Any]:
    """
    Celery task to asynchronously parse, chunk, store and vector-index a single PDF judgment.
    """
    filename = os.path.basename(pdf_path)
    self.update_state(
        state="PROGRESS",
        meta={"file": filename, "status": "processing", "stage": "extraction"}
    )
    
    # Import inside task to keep worker initialization clean
    from services.batch_service import process_single_pdf
    
    result = process_single_pdf(
        pdf_path=pdf_path,
        output_folder=output_folder,
        qdrant_output_folder=qdrant_output_folder,
        court_type=court_type,
        embed=embed,
        sync_db=sync_db,
        sync_r2=sync_r2,
    )
    return result
