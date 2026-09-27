"""
LexLink - Batch CLI (Distributed Celery + Redis / Local)
=========================================================
Bulk judgment ingestion CLI powered by BatchIngestionService.

Start Celery Worker (Terminal 1):
    # On Windows:
    celery -A celery_app worker --loglevel=info -P solo

    # On Linux / macOS / WSL:
    celery -A celery_app worker --loglevel=info --concurrency=4

Usage (Terminal 2):
    # Process & embed first 5 PDFs using Celery + Redis:
    python batch_cli.py supreme_court_judgments chunked_output --limit 5

    # Force local in-process / ProcessPoolExecutor execution:
    python batch_cli.py supreme_court_judgments chunked_output --limit 10 --engine local --workers 4

    # Process and sync to Supabase database & Cloudflare R2:
    python batch_cli.py supreme_court_judgments chunked_output --sync-db --sync-r2

    # Chunk only without vector embedding:
    python batch_cli.py supreme_court_judgments chunked_output --no-embed

    # Export all Qdrant collection points to a JSON file:
    python batch_cli.py supreme_court_judgments chunked_output --export-qdrant all_qdrant_dump.json
"""

import sys
import time
import argparse

from models.batch import BatchConfig
from services.batch_service import BatchIngestionService
from qdrant_manager import export_collection_to_json, get_qdrant_status


def cli_progress_callback(res: dict, index: int, total: int, t0: float):
    """Formats and prints CLI real-time progress updates."""
    if res["status"] == "failed":
        print(f"[{index}/{total}] FAILED: {res['file']} - {res.get('reason')}")
    elif res["status"] == "skipped":
        print(f"[{index}/{total}] SKIPPED: {res['file']} - {res.get('reason')}")
    else:
        qd_info = f" | Qdrant: {res.get('qdrant_points', 0)} pts" if res.get("qdrant_embedded") else ""
        db_info = " | DB: synced" if res.get("db_persisted") else ""
        r2_info = " | R2: uploaded" if res.get("r2_url") else ""

        if index % 5 == 0 or index == total:
            elapsed = time.time() - t0
            rate = index / elapsed if elapsed > 0 else 0
            eta_min = (total - index) / rate / 60 if rate > 0 else 0
            print(f"[{index}/{total}] {res['file']}{qd_info}{db_info}{r2_info} ({rate:.1f} pdf/s, ETA {eta_min:.1f} min)")
        else:
            print(f"[{index}/{total}] {res['file']}{qd_info}{db_info}{r2_info}")


def main():
    parser = argparse.ArgumentParser(description="Bulk PDF Judgment Ingestion & Vector Indexing for LexLink")
    parser.add_argument("input_path", nargs="?", default="supreme_court_judgments", help="Directory of PDFs or a single PDF file")
    parser.add_argument("output_folder", nargs="?", default="chunked_output", help="Directory where per-PDF JSON output is saved")
    parser.add_argument("--qdrant-output", default=None, help="Folder for Qdrant verification JSON output (default: output_folder/qdrant_output)")
    parser.add_argument("--court-type", default=None, help="Declared court jurisdiction (SC / HC / DC)")
    parser.add_argument("--limit", type=int, default=5, help="Process only first N PDFs (default: 5). Use 0 for all.")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel worker processes for local execution (default: 1)")
    parser.add_argument("--engine", choices=["celery", "local"], default="celery", help="Execution engine: 'celery' (distributed queue) or 'local' (ProcessPoolExecutor/sequential)")
    parser.add_argument("--no-resume", action="store_true", help="Reprocess PDFs even if output JSON already exists")
    parser.add_argument("--no-embed", action="store_true", help="Skip Qdrant embedding and only generate chunk JSONs")
    parser.add_argument("--sync-db", action="store_true", help="Persist documents and chunks into Supabase database")
    parser.add_argument("--sync-r2", action="store_true", help="Upload original PDF files to Cloudflare R2 bucket")
    parser.add_argument("--export-qdrant", type=str, default=None, help="Export entire Qdrant vector collection to a JSON file")

    args = parser.parse_args()

    if args.export_qdrant:
        print(f"[Qdrant Export] Exporting collection to {args.export_qdrant}...")
        export_collection_to_json(args.export_qdrant, include_full_vectors=False)
        sys.exit(0)

    config = BatchConfig(
        input_path=args.input_path,
        output_folder=args.output_folder,
        qdrant_output_folder=args.qdrant_output,
        court_type=args.court_type,
        embed=not args.no_embed,
        sync_db=args.sync_db,
        sync_r2=args.sync_r2,
        limit=None if args.limit == 0 else args.limit,
        workers=args.workers,
        resume=not args.no_resume,
        engine=args.engine,
    )

    q_status = get_qdrant_status() if config.embed else None

    print("=" * 70)
    print("LEXLINK BATCH INGESTION ENGINE (CELERY + REDIS / LOCAL)")
    print("=" * 70)
    print(f"Target Input      : {config.input_path}")
    print(f"Output Folder     : {config.output_folder}")
    print(f"Target Engine     : {config.engine.upper()} (with auto-fallback to local if broker unreachable)")
    if config.engine == "local":
        print(f"Workers (Local)   : {config.workers}")
    print(f"Court Type Tag    : {config.court_type or 'Auto-detect'}")
    print(f"Resume Mode       : {'ENABLED' if config.resume else 'DISABLED'}")
    print(f"Supabase DB Sync  : {'ENABLED' if config.sync_db else 'DISABLED'}")
    print(f"Cloudflare R2 Sync: {'ENABLED' if config.sync_r2 else 'DISABLED'}")
    if config.embed and q_status:
        print(f"Qdrant Embedding  : ENABLED | Model: {q_status.get('embedding_model')} ({q_status.get('vector_dimension')}-dim)")
    else:
        print("Qdrant Embedding  : DISABLED")
    print("=" * 70)

    summary = BatchIngestionService.run_batch(config=config, progress_callback=cli_progress_callback)

    print("\n" + "=" * 70)
    print("BATCH RUN COMPLETE")
    print("=" * 70)
    print(f"Engine Used            : {summary.engine_used.upper() if summary.engine_used else 'LOCAL'}")
    print(f"Total PDFs Found       : {summary.total_found}")
    print(f"Already Done (Skipped) : {summary.skipped_already_done}")
    print(f"Processed This Run     : {summary.total_processed}")
    print(f"Successful             : {summary.successful}")
    print(f"Qdrant Points Indexed  : {summary.total_qdrant_points}")
    print(f"Skipped (Unreadable)   : {len(summary.skipped_unreadable)}")
    print(f"Failed                 : {len(summary.failed)}")
    print(f"Total Time             : {summary.elapsed_seconds/60:.2f} min ({summary.elapsed_seconds:.1f}s)")
    print(f"Audit Log Saved To     : {summary.log_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()