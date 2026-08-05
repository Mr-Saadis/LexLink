"""
LexLink - Batch CLI (offline, resumable, parallel)
====================================================
Yeh 4000+ PDFs ko ek folder se process karke per-PDF JSON output banata
hai. Ab dono court types (SC + HC) ke liye SAME judgment_pipeline.py use
karta hai, isliye do alag scripts maintain karne ki zarurat nahi.

Usage:
    python3 batch_cli.py <input_folder> <output_folder> --limit 0 --workers 4
    python3 batch_cli.py <input_folder> <output_folder> --court-type HC
"""

import os
import sys
import json
import time
import argparse

from judgment_pipeline import process_pdf


def _process_one(args):
    pdf_path, output_folder, court_type = args
    out_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
    out_path = os.path.join(output_folder, out_name)
    try:
        result = process_pdf(pdf_path, declared_court_type=court_type)
        if "error" in result:
            return {"file": os.path.basename(pdf_path), "status": "skipped", "reason": result["error"]}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return {
            "file": os.path.basename(pdf_path), "status": "success",
            "chunks": result["total_chunks"],
            "judge": result["metadata"]["judge"],
            "case_number": result["metadata"]["case_number"],
        }
    except Exception as e:
        return {"file": os.path.basename(pdf_path), "status": "failed", "reason": str(e)}


def batch_process(input_path, output_folder, court_type=None, limit=None, workers=1, resume=True):
    os.makedirs(output_folder, exist_ok=True)

    if os.path.isdir(input_path):
        pdf_files = sorted([
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(".pdf")
        ])
    else:
        pdf_files = [input_path]

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

    print("=" * 70)
    print(f"Processing {len(pdf_files)} PDF(s)"
          + (f" (skipping {skipped_already_done} already done - resume mode)" if skipped_already_done else ""))
    print(f"Workers: {workers} | Declared court_type: {court_type or 'not set (auto-detect only)'}")
    print("=" * 70)

    success, skipped, failed = 0, [], []
    tasks = [(p, output_folder, court_type) for p in pdf_files]
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
            elif r["status"] == "skipped":
                skipped.append(r)
            else:
                failed.append(r)

    log_path = os.path.join(output_folder, "_run_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"failed": failed, "skipped_unreadable": skipped}, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("RUN COMPLETE")
    print("=" * 70)
    print(f"Processed : {len(pdf_files)}")
    print(f"Successful: {success}")
    print(f"Skipped (unreadable/scanned): {len(skipped)}")
    print(f"Failed    : {len(failed)}")
    print(f"Time      : {elapsed/60:.1f} min ({elapsed/max(len(pdf_files),1):.1f} sec/pdf avg)")
    print(f"Log       : {log_path}")
    print("=" * 70)


def _handle_result(r, i, total, t0):
    if r["status"] == "failed":
        print(f"[{i}/{total}] FAILED: {r['file']} - {r['reason']}")
    elif i % 25 == 0 or i == total:
        elapsed = time.time() - t0
        rate = i / elapsed if elapsed > 0 else 0
        eta_min = (total - i) / rate / 60 if rate > 0 else 0
        print(f"[{i}/{total}] ... ({rate:.1f} pdf/s, ETA {eta_min:.0f} min)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk SC + HC judgment PDFs for RAG ingestion (unified pipeline)")
    parser.add_argument("input_path", help="Folder of PDFs or a single PDF file")
    parser.add_argument("output_folder", help="Where per-PDF JSON output goes")
    parser.add_argument("--court-type", default=None, help="Declared court type to tag output with (SC / HC / DC) - does not change extraction logic")
    parser.add_argument("--limit", type=int, default=5, help="Process only first N PDFs (default: 5). Use --limit 0 for all PDFs.")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker processes (e.g. 4-8)")
    parser.add_argument("--no-resume", action="store_true", help="Reprocess PDFs even if output JSON already exists")
    args = parser.parse_args()
    limit = None if args.limit == 0 else args.limit
    batch_process(args.input_path, args.output_folder, court_type=args.court_type,
                  limit=limit, workers=args.workers, resume=not args.no_resume)