"""
LexLink - Judgment Sorter Script (Header-Only Matching)
==========================================================
Kaam: EK folder (jisme Supreme Court + High Court dono ke PDFs mixed
hain) ko scan karta hai, HAR PDF ke document HEADER (shuruati hissa)
se text nikal kar us me court-name pattern dhoondta hai, aur PDF ko
teen destination folders me se ek me MOVE/COPY kar deta hai.

FIX: Sirf document ke shuruati ~600 characters me search karte hain
(jahan court ka naam hamesha likha hota hai jaise "IN THE SUPREME
COURT OF PAKISTAN" ya "IN THE LAHORE HIGH COURT"). Poora document
scan NAHI karte, kyunke High Court judgments me bhi Supreme Court
ke case-citations hote hain jo false-positive detection karte thay.

Run karne ke liye:
    pip install pymupdf
    python sort_judgments.py --source "D:\\data_sources\\judgments"

Debug mode (ek file ka text dekhne ke liye):
    python sort_judgments.py --debug-file "D:\\path\\to\\one.pdf"
"""

import os
import re
import shutil
import argparse
import fitz  # PyMuPDF


# ----------------------------------------------------------------------
# COURT DETECTION PATTERNS
# ----------------------------------------------------------------------
_SUPREME_RE = re.compile(
    r"SUPREME\s+COURT\s+OF\s+PAKISTAN",
    re.IGNORECASE
)

_HIGH_COURT_RE = re.compile(
    r"(LAHORE\s+HIGH\s+COURT|SINDH\s+HIGH\s+COURT|PESHAWAR\s+HIGH\s+COURT|"
    r"ISLAMABAD\s+HIGH\s+COURT|BALOCHISTAN\s+HIGH\s+COURT|"
    r"HIGH\s+COURT\s+OF\s+[\w\s]+?(?:AT\s+\w+)?)",
    re.IGNORECASE
)

_GENERIC_HIGH_COURT_RE = re.compile(r"\bHIGH\s+COURT\b", re.IGNORECASE)
_GENERIC_SUPREME_RE = re.compile(r"\bSUPREME\s+COURT\b", re.IGNORECASE)

PAGES_TO_SCAN = 2
HEADER_CHAR_LIMIT = 600


def normalize_text(text):
    text = re.sub(r"[\xa0\u2000-\u200b\u202f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_court_type(pdf_path, debug=False):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        if debug:
            print(f"  [DEBUG] PDF open failed: {e}")
        return "unreadable"

    raw_text = ""
    try:
        pages_to_check = min(PAGES_TO_SCAN, len(doc))
        for page_num in range(pages_to_check):
            raw_text += doc[page_num].get_text() + "\n"
    finally:
        doc.close()

    if not raw_text.strip():
        if debug:
            print("  [DEBUG] Koi text extract hi nahi hua")
        return "unreadable"

    full_text = normalize_text(raw_text)
    header_text = full_text[:HEADER_CHAR_LIMIT]

    if debug:
        print(f"  [DEBUG] Header text (searched region):\n  {header_text}\n")

    if _SUPREME_RE.search(header_text):
        if debug:
            print("  [DEBUG] Matched: SPECIFIC Supreme Court (in header)")
        return "supreme"

    if _HIGH_COURT_RE.search(header_text):
        if debug:
            print("  [DEBUG] Matched: SPECIFIC High Court (in header)")
        return "high"

    if _GENERIC_SUPREME_RE.search(header_text):
        if debug:
            print("  [DEBUG] Matched: GENERIC Supreme Court (in header)")
        return "supreme"

    if _GENERIC_HIGH_COURT_RE.search(header_text):
        if debug:
            print("  [DEBUG] Matched: GENERIC High Court (in header)")
        return "high"

    if debug:
        print("  [DEBUG] Koi pattern match nahi hua (header me)")

    return "unmatched"


def already_sorted(filename, supreme_folder, high_folder, unmatched_folder):
    return (
        os.path.exists(os.path.join(supreme_folder, filename)) or
        os.path.exists(os.path.join(high_folder, filename)) or
        os.path.exists(os.path.join(unmatched_folder, filename))
    )


def sort_judgments(source_folder, dest_root=None, move_files=True):
    if dest_root is None:
        dest_root = source_folder

    supreme_folder = os.path.join(dest_root, "Supreme_Court")
    high_folder = os.path.join(dest_root, "High_Court")
    unmatched_folder = os.path.join(dest_root, "Unmatched")

    for folder in (supreme_folder, high_folder, unmatched_folder):
        os.makedirs(folder, exist_ok=True)

    pdf_files = [
        f for f in os.listdir(source_folder)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print(f"Koi PDF nahi mili is folder me: {source_folder}")
        return

    print(f"Total {len(pdf_files)} PDFs mili. Processing shuru...\n")

    counts = {"supreme": 0, "high": 0, "unmatched": 0, "unreadable": 0}
    skipped_count = 0
    action_fn = shutil.move if move_files else shutil.copy2
    action_word = "Moved" if move_files else "Copied"

    for i, filename in enumerate(pdf_files, start=1):
        if already_sorted(filename, supreme_folder, high_folder, unmatched_folder):
            skipped_count += 1
            print(f"[{i}/{len(pdf_files)}] {filename}  ->  SKIPPED (already sorted)")
            continue

        src_path = os.path.join(source_folder, filename)

        if not os.path.exists(src_path):
            print(f"[{i}/{len(pdf_files)}] {filename}  ->  SKIPPED (not in source)")
            continue

        result = detect_court_type(src_path)

        if result == "supreme":
            dest_path = os.path.join(supreme_folder, filename)
            counts["supreme"] += 1
        elif result == "high":
            dest_path = os.path.join(high_folder, filename)
            counts["high"] += 1
        else:
            dest_path = os.path.join(unmatched_folder, filename)
            counts["unmatched" if result == "unmatched" else "unreadable"] += 1

        try:
            action_fn(src_path, dest_path)
        except OSError as e:
            print(f"\nERROR: {e}")
            print(f"Rukk gaya file #{i} pe: {filename}")
            print("Disk space free karein aur yehi command dobara chalayein (resume-safe hai).")
            return

        print(f"[{i}/{len(pdf_files)}] {filename}  ->  {result.upper()}  ({action_word})")

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Supreme Court matched : {counts['supreme']}")
    print(f"High Court matched    : {counts['high']}")
    print(f"Unmatched (no pattern): {counts['unmatched']}")
    print(f"Unreadable (corrupt/scanned): {counts['unreadable']}")
    print(f"Skipped (already sorted): {skipped_count}")
    print(f"\nOutput folders:")
    print(f"  {supreme_folder}")
    print(f"  {high_folder}")
    print(f"  {unmatched_folder}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Judgment PDFs ko Supreme Court / High Court / Unmatched me sort karta hai (header-only matching)."
    )
    parser.add_argument("--source", help="Mixed PDFs wala source folder")
    parser.add_argument("--dest-root", default=None, help="Output folders yahan banenge")
    parser.add_argument("--copy", action="store_true", help="Files COPY karein. Default: MOVE.")
    parser.add_argument(
        "--debug-file", default=None,
        help="Sirf EK PDF ka header text dikhao (sorting nahi karega)"
    )

    args = parser.parse_args()

    if args.debug_file:
        print(f"Debugging: {args.debug_file}\n")
        result = detect_court_type(args.debug_file, debug=True)
        print(f"\nFinal detection result: {result.upper()}")
    else:
        if not args.source:
            parser.error("--source is required unless --debug-file is used")
        sort_judgments(
            source_folder=args.source,
            dest_root=args.dest_root,
            move_files=not args.copy,
        )