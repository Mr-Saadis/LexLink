import os
import json
import time
import uuid
from typing import List, Optional, Callable, Dict, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from models.batch import BatchConfig, BatchFileResult, BatchSummary
from judgement_pipeline import process_pdf
from qdrant_manager import upsert_judgment_chunks, get_qdrant_status


def _worker_task(args: Tuple[str, str, str, Optional[str], bool, bool, bool]) -> Dict[str, Any]:
    """Top-level worker function required for multiprocessing serialization."""
    pdf_path, output_folder, qdrant_output_folder, court_type, embed, sync_db, sync_r2 = args
    return process_single_pdf(
        pdf_path=pdf_path,
        output_folder=output_folder,
        qdrant_output_folder=qdrant_output_folder,
        court_type=court_type,
        embed=embed,
        sync_db=sync_db,
        sync_r2=sync_r2,
    )


def process_single_pdf(
    pdf_path: str,
    output_folder: str,
    qdrant_output_folder: str,
    court_type: Optional[str] = None,
    embed: bool = True,
    sync_db: bool = False,
    sync_r2: bool = False,
) -> Dict[str, Any]:
    """
    Parses a single PDF judgment, outputs chunked JSON,
    and optionally executes R2 storage, DB persistence, and Qdrant vector indexing.
    """
    filename = os.path.basename(pdf_path)
    out_name = os.path.splitext(filename)[0] + ".json"
    out_path = os.path.join(output_folder, out_name)

    try:
        result = process_pdf(pdf_path, declared_court_type=court_type)
        if "error" in result:
            return {
                "file": filename,
                "status": "skipped",
                "reason": result["error"],
            }

        # 1. Save standard chunked JSON to disk
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        r2_url = None
        doc_id = None
        db_persisted = False

        # 2. Optional Cloudflare R2 upload
        if sync_r2:
            try:
                from r2_client import is_r2_configured, upload_file_to_r2
                if is_r2_configured():
                    object_key = f"judgments/{uuid.uuid4()}_{filename}"
                    r2_url = upload_file_to_r2(pdf_path, object_key, content_type="application/pdf")
            except Exception as r2_err:
                print(f"[Batch Sync R2 Warning] {filename}: {r2_err}")

        # 3. Optional Supabase Database insertion
        if sync_db:
            try:
                from supabase_client import is_supabase_configured, save_judgment_to_supabase
                if is_supabase_configured():
                    db_res = save_judgment_to_supabase(result_data=result, pdf_url=r2_url)
                    if db_res:
                        doc_id = db_res.get("document_id")
                        db_persisted = True
            except Exception as db_err:
                print(f"[Batch Sync DB Warning] {filename}: {db_err}")

        # 4. Optional Qdrant vector embedding
        qdrant_result = None
        if embed and result.get("chunks"):
            qdrant_result = upsert_judgment_chunks(
                result_data=result,
                document_id=doc_id,
                save_json_file=True,
                output_dir=qdrant_output_folder,
                include_full_vectors_in_json=True,
            )

        metadata = result.get("metadata", {})
        return {
            "file": filename,
            "status": "success",
            "chunks": result.get("total_chunks", 0),
            "judge": metadata.get("judge"),
            "case_number": metadata.get("case_number"),
            "qdrant_embedded": bool(qdrant_result and qdrant_result.get("success")),
            "qdrant_points": qdrant_result.get("points_upserted", 0) if qdrant_result else 0,
            "qdrant_json": qdrant_result.get("qdrant_json_path") if qdrant_result else None,
            "db_persisted": db_persisted,
            "r2_url": r2_url,
        }
    except Exception as e:
        return {
            "file": filename,
            "status": "failed",
            "reason": str(e),
        }


class BatchIngestionService:
    """
    Reusable and scalable batch processing engine for court judgments.
    """

    @staticmethod
    def resolve_target_files(input_path: str, output_folder: str, resume: bool = True) -> Tuple[List[str], int, int]:
        """
        Discovers PDF files from input directory or file path and calculates resume skips.
        """
        target_path = input_path
        if not os.path.exists(target_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_candidate = os.path.join(os.path.dirname(backend_dir), input_path)
            if os.path.exists(workspace_candidate):
                target_path = workspace_candidate
            else:
                target_path = os.path.join(backend_dir, input_path)

        if os.path.isdir(target_path):
            pdf_files = sorted([
                os.path.join(target_path, f)
                for f in os.listdir(target_path)
                if f.lower().endswith(".pdf")
            ])
        elif os.path.isfile(target_path):
            pdf_files = [target_path]
        else:
            pdf_files = []

        total_found = len(pdf_files)
        skipped_already_done = 0

        if resume:
            filtered_files = [
                p for p in pdf_files
                if not os.path.exists(os.path.join(output_folder, os.path.splitext(os.path.basename(p))[0] + ".json"))
            ]
            skipped_already_done = total_found - len(filtered_files)
            pdf_files = filtered_files

        return pdf_files, total_found, skipped_already_done

    @classmethod
    def run_batch(
        cls,
        config: BatchConfig,
        progress_callback: Optional[Callable[[Dict[str, Any], int, int, float], None]] = None,
    ) -> BatchSummary:
        """
        Executes batch ingestion according to the provided configuration.
        """
        os.makedirs(config.output_folder, exist_ok=True)
        qdrant_out_dir = config.qdrant_output_folder or os.path.join(config.output_folder, "qdrant_output")
        os.makedirs(qdrant_out_dir, exist_ok=True)

        pdf_files, total_found, skipped_already_done = cls.resolve_target_files(
            input_path=config.input_path,
            output_folder=config.output_folder,
            resume=config.resume,
        )

        if config.limit and config.limit > 0:
            pdf_files = pdf_files[:config.limit]

        tasks = [
            (
                p,
                config.output_folder,
                qdrant_out_dir,
                config.court_type,
                config.embed,
                config.sync_db,
                config.sync_r2,
            )
            for p in pdf_files
        ]

        total_to_process = len(tasks)
        success_count = 0
        total_qdrant_points = 0
        skipped_unreadable: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []

        t0 = time.time()
        engine_used = "local"

        use_celery = config.engine == "celery"
        if use_celery:
            try:
                from celery_app import is_redis_available
                if is_redis_available():
                    engine_used = "celery"
                else:
                    print("[Batch Engine Notice] Redis broker not reachable at configured URL. Gracefully falling back to local execution.")
            except Exception as chk_err:
                print(f"[Batch Engine Notice] Celery check failed ({chk_err}). Falling back to local execution.")

        if engine_used == "celery" and total_to_process > 0:
            try:
                from celery import group
                from tasks.batch_tasks import process_pdf_judgment_task

                celery_group = group(
                    process_pdf_judgment_task.s(
                        pdf_path=t[0],
                        output_folder=t[1],
                        qdrant_output_folder=t[2],
                        court_type=t[3],
                        embed=t[4],
                        sync_db=t[5],
                        sync_r2=t[6],
                    )
                    for t in tasks
                )
                group_async = celery_group.apply_async()

                completed_indices = set()
                while not group_async.ready():
                    for idx, async_res in enumerate(group_async.results):
                        if idx not in completed_indices and async_res.ready():
                            completed_indices.add(idx)
                            try:
                                res = async_res.get(timeout=1)
                            except Exception as ex:
                                res = {
                                    "file": os.path.basename(tasks[idx][0]),
                                    "status": "failed",
                                    "reason": str(ex),
                                }

                            if progress_callback:
                                progress_callback(res, len(completed_indices), total_to_process, t0)

                            if res["status"] == "success":
                                success_count += 1
                                total_qdrant_points += res.get("qdrant_points", 0)
                            elif res["status"] == "skipped":
                                skipped_unreadable.append(res)
                            else:
                                failed.append(res)
                    time.sleep(0.2)

                # Collect any remaining finished results
                for idx, async_res in enumerate(group_async.results):
                    if idx not in completed_indices:
                        completed_indices.add(idx)
                        try:
                            res = async_res.get(timeout=5)
                        except Exception as ex:
                            res = {
                                "file": os.path.basename(tasks[idx][0]),
                                "status": "failed",
                                "reason": str(ex),
                            }

                        if progress_callback:
                            progress_callback(res, len(completed_indices), total_to_process, t0)

                        if res["status"] == "success":
                            success_count += 1
                            total_qdrant_points += res.get("qdrant_points", 0)
                        elif res["status"] == "skipped":
                            skipped_unreadable.append(res)
                        else:
                            failed.append(res)

            except Exception as celery_err:
                print(f"[Batch Engine Error] Celery group execution failed ({celery_err}). Falling back to local execution.")
                engine_used = "local"

        if engine_used == "local":
            if config.workers > 1 and total_to_process > 1:
                with ProcessPoolExecutor(max_workers=config.workers) as executor:
                    futures = {executor.submit(_worker_task, t): t for t in tasks}
                    for i, fut in enumerate(as_completed(futures), start=1):
                        res = fut.result()
                        if progress_callback:
                            progress_callback(res, i, total_to_process, t0)

                        if res["status"] == "success":
                            success_count += 1
                            total_qdrant_points += res.get("qdrant_points", 0)
                        elif res["status"] == "skipped":
                            skipped_unreadable.append(res)
                        else:
                            failed.append(res)
            else:
                for i, t in enumerate(tasks, start=1):
                    res = _worker_task(t)
                    if progress_callback:
                        progress_callback(res, i, total_to_process, t0)

                    if res["status"] == "success":
                        success_count += 1
                        total_qdrant_points += res.get("qdrant_points", 0)
                    elif res["status"] == "skipped":
                        skipped_unreadable.append(res)
                    else:
                        failed.append(res)

        elapsed = time.time() - t0
        log_path = os.path.join(config.output_folder, "_run_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_found": total_found,
                "total_processed": total_to_process,
                "successful": success_count,
                "skipped_already_done": skipped_already_done,
                "skipped_unreadable": skipped_unreadable,
                "failed": failed,
                "total_qdrant_points": total_qdrant_points,
                "elapsed_seconds": round(elapsed, 2),
                "engine_used": engine_used,
            }, f, ensure_ascii=False, indent=2)

        return BatchSummary(
            total_found=total_found,
            total_processed=total_to_process,
            successful=success_count,
            skipped_unreadable=skipped_unreadable,
            skipped_already_done=skipped_already_done,
            failed=failed,
            total_qdrant_points=total_qdrant_points,
            elapsed_seconds=round(elapsed, 2),
            log_path=log_path,
            engine_used=engine_used,
        )

