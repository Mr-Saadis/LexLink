"""
LexLink - Batch CLI (offline, resumable, parallel)
====================================================
Yeh 4000+ PDFs ko ek folder se process karke per-PDF JSON output banata
hai, BAAI/bge-m3 se dense embeddings generate karke Qdrant vector database
me index karta hai, aur Qdrant verification JSON files generate karta hai.

Usage:
    # Process & embed first 5 PDFs into Qdrant + chunked JSON + Qdrant JSON:
    python3 batch_cli.py supreme_court_judgments chunked_output --limit 5

    # Process all PDFs with Qdrant vector indexing:
    python3 batch_cli.py supreme_court_judgments chunked_output --limit 0 --workers 2

    # Chunk only without embedding:
    python3 batch_cli.py supreme_court_judgments chunked_output --no-embed

    # Export all Qdrant collection points to a JSON file for inspection:
    python3 batch_cli.py supreme_court_judgments chunked_output --export-qdrant all_qdrant_dump.json
"""

import os
import sys
import json
import time
import argparse

from judgement_pipeline import process_pdf
from qdrant_manager import upsert_judgment_chunks, export_collection_to_json, get_qdrant_status


def _process_one(args):
    pdf_path, output_folder, qdrant_output_folder, court_type, embed_to_qdrant = args
    out_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
    out_path = os.path.join(output_folder, out_name)
    try:
        result = process_pdf(pdf_path, declared_court_type=court_type)
        if "error" in result:
            return {"file": os.path.basename(pdf_path), "status": "skipped", "reason": result["error"]}
        
        # Save standard chunked JSON
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        qdrant_result = None
        if embed_to_qdrant and result.get("chunks"):
            qdrant_result = upsert_judgment_chunks(
                result_data=result,
                save_json_file=True,
                output_dir=qdrant_output_folder,
                include_full_vectors_in_json=True,
            )

        return {
            "file": os.path.basename(pdf_path),
            "status": "success",
            "chunks": result["total_chunks"],
            "judge": result["metadata"]["judge"],
            "case_number": result["metadata"]["case_number"],
            "qdrant_embedded": bool(qdrant_result and qdrant_result.get("success")),
            "qdrant_points": qdrant_result.get("points_upserted", 0) if qdrant_result else 0,
            "qdrant_json": qdrant_result.get("qdrant_json_path") if qdrant_result else None,
        }
    except Exception as e:
        return {"file": os.path.basename(pdf_path), "status": "failed", "reason": str(e)}


def batch_process(
    input_path,
    output_folder,
    qdrant_output_folder=None,
    court_type=None,
    embed=True,
    limit=None,
    workers=1,
    resume=True,
):
    os.makedirs(output_folder, exist_ok=True)
    qdrant_out_dir = qdrant_output_folder or os.path.join(output_folder, "qdrant_output")
    target_path = input_path
    if not os.path.exists(target_path):
        workspace_candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), input_path)
        if os.path.exists(workspace_candidate):
            target_path = workspace_candidate

    if os.path.isdir(target_path):
        pdf_files = sorted([
            os.path.join(target_path, f)
            for f in os.listdir(target_path)
            if f.lower().endswith(".pdf")
        ])
    else:
        pdf_files = [target_path]

    skipped_already_done = 0
    if resume:
        before = len(pdf_files)
        pdf_files = [
            p for p in pdf_files
            if not os.path.exists(os.path.join(output_folder, os.path.splitext(os.path.basename(p))[0] + ".json"))
        ]
        skipped_already_done = before - len(pdf_files)

    if limit:
        pdf_files = pdf_files[:limit]

    q_status = get_qdrant_status() if embed else None

    print("=" * 70)
    print(f"Processing {len(pdf_files)} PDF(s)"
          + (f" (skipping {skipped_already_done} already done - resume mode)" if skipped_already_done else ""))
    print(f"Workers: {workers} | Declared court_type: {court_type or 'not set (auto-detect only)'}")
    if embed and q_status:
        print(f"Qdrant Embedding: ENABLED | Model: {q_status.get('embedding_model')} ({q_status.get('vector_dimension')}-dim)")
        print(f"Qdrant Mode: {q_status.get('mode')} | Collection: {q_status.get('collection_name')}")
        print(f"Qdrant JSON Output Folder: {qdrant_out_dir}")
    else:
        print("Qdrant Embedding: DISABLED")
    print("=" * 70)

    success, skipped, failed = 0, [], []
    total_qdrant_points = 0
    tasks = [(p, output_folder, qdrant_out_dir, court_type, embed) for p in pdf_files]
    t0 = time.time()

    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_process_one, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), start=1):
                r = fut.result()
                _handle_result(r, i, len(tasks), t0)
                if r["status"] == "success":
                    success += 1
                    total_qdrant_points += r.get("qdrant_points", 0)
                elif r["status"] == "skipped":
                    skipped.append(r)
                else:
                    failed.append(r)
    else:
        for i, t in enumerate(tasks, start=1):
            r = _process_one(t)
            _handle_result(r, i, len(tasks), t0)
            if r["status"] == "success":
                success += 1
                total_qdrant_points += r.get("qdrant_points", 0)
            elif r["status"] == "skipped":
                skipped.append(r)
            else:
                failed.append(r)

    log_path = os.path.join(output_folder, "_run_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "failed": failed,
            "skipped_unreadable": skipped,
            "total_qdrant_points_embedded": total_qdrant_points,
        }, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("RUN COMPLETE")
    print("=" * 70)
    print(f"Processed          : {len(pdf_files)}")
    print(f"Successful         : {success}")
    print(f"Qdrant Points Indexed: {total_qdrant_points}")
    print(f"Skipped (unreadable): {len(skipped)}")
    print(f"Failed             : {len(failed)}")
    print(f"Time               : {elapsed/60:.1f} min ({elapsed/max(len(pdf_files),1):.1f} sec/pdf avg)")
    print(f"Log                : {log_path}")
    if embed:
        print(f"Qdrant JSON Output : {qdrant_out_dir}")
    print("=" * 70)


def _handle_result(r, i, total, t0):
    if r["status"] == "failed":
        print(f"[{i}/{total}] FAILED: {r['file']} - {r['reason']}")
    else:
        qd_info = f" | Qdrant: {r.get('qdrant_points', 0)} pts" if r.get("qdrant_embedded") else ""
        if i % 10 == 0 or i == total:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta_min = (total - i) / rate / 60 if rate > 0 else 0
            print(f"[{i}/{total}] {r['file']}{qd_info} ({rate:.1f} pdf/s, ETA {eta_min:.0f} min)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk SC + HC judgment PDFs & embed into Qdrant for RAG ingestion")
    parser.add_argument("input_path", nargs="?", default="supreme_court_judgments", help="Folder of PDFs or a single PDF file")
    parser.add_argument("output_folder", nargs="?", default="chunked_output", help="Where per-PDF JSON output goes")
    parser.add_argument("--qdrant-output", default=None, help="Custom folder for Qdrant verification JSON output (default: output_folder/qdrant_output)")
    parser.add_argument("--court-type", default=None, help="Declared court type to tag output with (SC / HC / DC)")
    parser.add_argument("--limit", type=int, default=5, help="Process only first N PDFs (default: 5). Use --limit 0 for all PDFs.")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker processes (default: 1)")
    parser.add_argument("--no-resume", action="store_true", help="Reprocess PDFs even if output JSON already exists")
    parser.add_argument("--no-embed", action="store_true", help="Skip Qdrant embedding and only generate chunk JSONs")
    parser.add_argument("--export-qdrant", type=str, default=None, help="Export entire Qdrant vector database collection to a JSON file")
    args = parser.parse_args()

    if args.export_qdrant:
        export_collection_to_json(args.export_qdrant, include_full_vectors=False)
        sys.exit(0)

    limit = None if args.limit == 0 else args.limit
    batch_process(
        input_path=args.input_path,
        output_folder=args.output_folder,
        qdrant_output_folder=args.qdrant_output,
        court_type=args.court_type,
        embed=not args.no_embed,
        limit=limit,
        workers=args.workers,
        resume=not args.no_resume,
    )