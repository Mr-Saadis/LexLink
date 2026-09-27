"""
LexLink - Unified Judgment PDF Pipeline
========================================
Ye file dono scripts (Supreme Court + LHC) ko MERGE karti hai taake ek hi
extraction script Supreme Court aur High Court, dono tarah ke judgments
pe consistently chale.

Pipeline (har PDF ke liye same):
    extract lines (+ bbox) -> sort into reading order
        -> remove boilerplate (normalized, works for SC's exact-repeat
           footers AND HC's page-number-changing footers)
        -> fixed-window chunk (with overlap)
        -> best-effort metadata (SC-style regex tried first, HC-style
           regex tried as fallback, judge/dates extracted always)
        -> return dict (caller decides: save as JSON, or return as API
           response, or push to Qdrant/Supabase)

Is module ko do jagah use kiya jata hai:
    1. batch_cli.py   -> 4000+ PDFs ko offline, resumable, parallel process
                         karne ke liye (process_pdf() use karta hai)
    2. api_server.py  -> "Select Files" button se upload hone wali single
                         PDF ko turant process karke, HAR STAGE ke baad
                         progress event stream karne ke liye
                         (process_pdf_stream() use karta hai)
"""

import fitz  # PyMuPDF
import re
import os
import uuid

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
TARGET_WORDS = 200
OVERLAP_WORDS = 40
MIN_CHUNK_WORDS = 30
BOILERPLATE_MIN_PAGES = 3

# Row-grouping tolerance (in PDF points) for reading-order sort below.
# Two lines whose y0 differ by less than this are treated as being on
# the "same visual row" and ordered left-to-right instead of by
# whichever happened to appear first in the content stream.
ROW_TOLERANCE = 3

# Kitni lines tak "Versus"/"Vs." ke aas-paas party-name search karni hai
# (dono directions me) - multi-line wrapped names aur beech me aane wali
# suffix-only lines dono ko cover karne ke liye.
_PARTY_SEARCH_WINDOW = 3


# ----------------------------------------------------------------------
# STEP 1: Line-level extraction with bbox + reading-order sort
# ----------------------------------------------------------------------
def extract_lines(pdf_path):
    """
    Har line ka: text, page number, bbox {x0,y0,x1,y1} nikalta hai.

    FIX: PyMuPDF ke "blocks" content-stream order me aate hain, jo
    multi-column / text-box headers (SC order-sheets me case-caption aur
    "PRESENT: <judges>" panel side-by-side hote hain) ke liye visual
    reading order NAHI hoti. Is liye har page ke baad lines ko
    (row-bucket(y0), x0) pe sort karte hain - top-to-bottom, aur same
    visual row ke andar left-to-right.
    """
    doc = fitz.open(pdf_path)
    lines = []
    for page_num, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict")
        page_lines = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block, skip images
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                x1 = max(s["bbox"][2] for s in spans)
                y1 = max(s["bbox"][3] for s in spans)
                page_lines.append({
                    "text": text,
                    "page": page_num,
                    "bbox": {"x0": round(x0, 1), "y0": round(y0, 1),
                             "x1": round(x1, 1), "y1": round(y1, 1)}
                })

        page_lines.sort(
            key=lambda ln: (round(ln["bbox"]["y0"] / ROW_TOLERANCE), ln["bbox"]["x0"])
        )
        lines.extend(page_lines)

    doc.close()
    return lines


# ----------------------------------------------------------------------
# STEP 2: Boilerplate removal (MERGED - uses the more general HC logic)
# ----------------------------------------------------------------------
FOOTER_TRAIL_NUM = re.compile(r"\s*\d{1,4}\s*$")


def _normalize_for_boilerplate(text):
    return FOOTER_TRAIL_NUM.sub("", text).strip()


def remove_boilerplate(lines):
    norm_to_pages = {}
    for ln in lines:
        norm = _normalize_for_boilerplate(ln["text"])
        if not norm or " " not in norm:
            continue
        norm_to_pages.setdefault(norm, set()).add(ln["page"])

    boilerplate_norms = {
        norm for norm, pages in norm_to_pages.items()
        if len(pages) >= BOILERPLATE_MIN_PAGES
    }

    cleaned = [
        ln for ln in lines
        if _normalize_for_boilerplate(ln["text"]) not in boilerplate_norms
    ]
    return cleaned, list(boilerplate_norms)


# ----------------------------------------------------------------------
# STEP 3: Fixed-window chunking with overlap (identical in both scripts)
# ----------------------------------------------------------------------
def build_chunks(lines, target_words=TARGET_WORDS, overlap_words=OVERLAP_WORDS):
    chunks = []
    current_lines = []
    current_word_count = 0

    def flush_chunk():
        if not current_lines:
            return None
        text = " ".join(ln["text"] for ln in current_lines)
        pages = sorted(set(ln["page"] for ln in current_lines))
        bboxes = [{"page": ln["page"], **ln["bbox"]} for ln in current_lines]
        return {
            "chunk_id": str(uuid.uuid4()),
            "text": text,
            "word_count": current_word_count,
            "page_start": pages[0],
            "page_end": pages[-1],
            "bbox": bboxes,
        }

    i = 0
    while i < len(lines):
        ln = lines[i]
        words_in_line = len(ln["text"].split())
        current_lines.append(ln)
        current_word_count += words_in_line
        i += 1

        if current_word_count >= target_words:
            chunk = flush_chunk()
            if chunk:
                chunks.append(chunk)
            overlap_lines = []
            overlap_count = 0
            for prev_ln in reversed(current_lines):
                w = len(prev_ln["text"].split())
                if overlap_count + w > overlap_words:
                    break
                overlap_lines.insert(0, prev_ln)
                overlap_count += w
            current_lines = overlap_lines
            current_word_count = overlap_count

    if current_lines and current_word_count >= MIN_CHUNK_WORDS:
        chunk = flush_chunk()
        if chunk:
            chunks.append(chunk)
    elif current_lines and chunks:
        tail_text = " ".join(ln["text"] for ln in current_lines)
        chunks[-1]["text"] += " " + tail_text
        chunks[-1]["word_count"] += current_word_count
        chunks[-1]["bbox"].extend({"page": ln["page"], **ln["bbox"]} for ln in current_lines)

    return chunks


# ----------------------------------------------------------------------
# STEP 4: Metadata extraction - MERGED
# ----------------------------------------------------------------------
def _normalize_spaces(text):
    return re.sub(r"[\xa0\u2000-\u200b\u202f]", " ", text)


# ---- Court name: union of both scripts' patterns ----
_COURT_RE = re.compile(
    r"(?:IN THE\s+)?(SUPREME COURT OF PAKISTAN|"
    r"LAHORE HIGH COURT|SINDH HIGH COURT|PESHAWAR HIGH COURT|"
    r"ISLAMABAD HIGH COURT|BALOCHISTAN HIGH COURT|"
    r"HIGH COURT OF[\w\s]+|[A-Z\s]+ TRIBUNAL)",
    re.IGNORECASE
)

# ---- Case number: SC style tried first, HC "Case No:" style next,
#      generic abbreviation style (R.F.A, F.A.O, C.R, Crl.A, I.C.A, ...)
#      as last-resort fallback ----
_CASE_NO_SC_RE = re.compile(
    r"((?:Civil|Criminal|Crl\.?|Const\.?|Writ|C\.?P\.?|W\.?P\.?)\s*"
    r"(?:Appeal|Petition|Application|Suit)?\s*No\.?\s*[\d/\-]+[A-Za-z]?\s*(?:of\s*\d{4})?)",
    re.IGNORECASE
)
_CASE_NO_HC_RE = re.compile(
    r"Case No\.?:?\s*([A-Za-z\.\s]*?\d[\d/\-\.\s]*(?:of\s*\d{4})?)\s+[A-Z][a-z]",
    re.IGNORECASE
)
# FIX (new): covers abbreviations like "R.F.A.No.171 of 2010",
# "F.A.O.No.55/2019", "Crl.A.No.123 of 2021" jo upar wale dono patterns
# ke fixed keyword-list me nahi thay. Requires dotted uppercase
# abbreviation (2+ letters) immediately followed by "No." + digits, so it
# won't accidentally match stray single-letter noise.
_CASE_NO_GENERIC_RE = re.compile(
    r"\b([A-Z]{1,6}(?:\.[A-Z]{1,6}){1,4}\.?\s*No\.?\s*[\d][\d/\-]*[A-Za-z]?\s*(?:of\s*\d{4})?)"
)

# ---- Parties: line-based (not blob-regex) ----
_PARTY_SUFFIX_RE = re.compile(
    r"\s*(?:…|\.\.\.)?\s*(?:Appellant|Petitioner|Plaintiff|Respondent|Defendant)s?\s*\(?s?\)?\s*$",
    re.IGNORECASE
)
_PARTY_SUFFIX_ONLY_RE = re.compile(
    r"\s*(?:…|\.\.\.)?\s*(?:Appellant|Petitioner|Plaintiff|Respondent|Defendant)s?\s*\(?s?\)?\s*",
    re.IGNORECASE
)
# FIX: "Vs."/"Vs" bhi accept karte hain, sirf "Versus" nahi (LHC judgments
# me "Vs." zyada common hai).
_VERSUS_STANDALONE_RE = re.compile(r"^(?:versus|vs\.?)$", re.IGNORECASE)
_PARTIES_INLINE_RE = re.compile(
    r"^([A-Z][\w\.\-\s&,]{2,80}?)\.?\s+(?:Versus|Vs\.?)\s+([A-Z][\w\.\-\s&,]{2,80}?)\.?$",
    re.IGNORECASE
)


def _is_suffix_only_line(t):
    return bool(re.fullmatch(_PARTY_SUFFIX_ONLY_RE, t))


def _collect_party_name(norm_lines, start_idx, step, window):
    """
    start_idx se `step` direction me (step=-1 = backward/appellant,
    step=+1 = forward/respondent) `window` lines tak chalte hain aur
    jitni bhi non-blank, non-suffix-only lines milen unhe ORIGINAL
    (ascending) order me collect + join kar dete hain.
    """
    collected = []
    idx = start_idx
    steps_taken = 0
    while 0 <= idx < len(norm_lines) and steps_taken < window:
        cand = norm_lines[idx]
        if cand and not _is_suffix_only_line(cand):
            collected.append((idx, cand))
        idx += step
        steps_taken += 1

    if not collected:
        return None

    collected.sort(key=lambda p: p[0])
    joined = " ".join(c[1] for c in collected)
    joined = _PARTY_SUFFIX_RE.sub("", joined).strip()
    joined = joined.rstrip(".").strip()
    return joined or None


def extract_parties_from_lines(lines):
    norm_lines = [_normalize_spaces(ln["text"]).strip() for ln in lines]

    # Case A: "Versus"/"Vs." alone on its own line (common SC layout)
    for i, t in enumerate(norm_lines):
        if _VERSUS_STANDALONE_RE.fullmatch(t):
            appellant = _collect_party_name(norm_lines, i - 1, -1, _PARTY_SEARCH_WINDOW)
            respondent = _collect_party_name(norm_lines, i + 1, +1, _PARTY_SEARCH_WINDOW)
            if appellant and respondent:
                return f"{appellant} vs {respondent}"

    # Case B: "X Versus Y" / "X Vs. Y" inline within a single line (HC layout)
    for t in norm_lines:
        m = _PARTIES_INLINE_RE.match(t)
        if m:
            return f"{m.group(1).strip()} vs {m.group(2).strip()}"

    return None


# ---- Dates of hearing: HC-specific field, harmless to always try ----
_HEARING_RE = re.compile(
    r"Dates? of hearing[:\s]*([0-9,\.\s\w]+?)(?:\n\s*\n|Petitioner|Respondent)",
    re.IGNORECASE
)

_MONTHS = (r"January|February|March|April|May|June|July|August|September|"
           r"October|November|December")
_DATE_RE = re.compile(
    rf"\b(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS}),?\s+\d{{4}}|\d{{1,2}}[./]\d{{1,2}}[./]\d{{2,4}})\b"
)

# ---- Judge name: line-based (HC script's approach), run always ----
_JUDGE_NAME_RE = re.compile(r"^([A-Z][A-Za-z\.\s]{3,45}?),?\s*J\s*[:.]-")
_JUDGE_SIG_RE = re.compile(r"^\(([A-Z][A-Za-z\.\s]{3,45}?)\)$")


def extract_judge_from_lines(lines):
    for ln in lines:
        text = _normalize_spaces(ln["text"]).strip()
        m = _JUDGE_NAME_RE.match(text)
        if m:
            return m.group(1).strip()

    for i, ln in enumerate(lines):
        text = _normalize_spaces(ln["text"]).strip()
        m = _JUDGE_SIG_RE.match(text)
        if m and i + 1 < len(lines) and lines[i + 1]["text"].strip().lower() == "judge":
            return m.group(1).strip()

    return None


def extract_metadata(full_text_first_page, lines, declared_court_type="SC"):
    text = _normalize_spaces(full_text_first_page)

    # Normalize declared_court_type to either "SC" or "HC" (default "SC")
    decl = (declared_court_type or "SC").strip().upper()
    if decl not in ("SC", "HC"):
        decl = "SC" if "supreme" in decl.lower() else "HC"

    meta = {
        "court": None,
        "declared_court_type": decl,
        "case_number": None,
        "parties": None,
        "judge": None,
        "dates_of_hearing": None,
        "date": None,
    }

    court_match = _COURT_RE.search(text)
    auto_court_type = None
    if court_match:
        meta["court"] = re.sub(r"\s+", " ", court_match.group(1)).strip()
        c_lower = meta["court"].lower()
        if "supreme" in c_lower:
            auto_court_type = "SC"
        elif "high court" in c_lower or "tribunal" in c_lower:
            auto_court_type = "HC"

    final_court_type = auto_court_type or decl
    meta["declared_court_type"] = decl

    # If court name was not detected from text, provide a sensible default name
    if not meta["court"]:
        meta["court"] = "SUPREME COURT OF PAKISTAN" if final_court_type == "SC" else "HIGH COURT"

    case_match = _CASE_NO_SC_RE.search(text)
    if case_match:
        meta["case_number"] = re.sub(r"\s+", " ", case_match.group(0)).strip()
    else:
        case_match = _CASE_NO_HC_RE.search(text)
        if case_match:
            meta["case_number"] = re.sub(r"\s+", " ", case_match.group(1)).strip().rstrip(".")
        else:
            case_match = _CASE_NO_GENERIC_RE.search(text)
            if case_match:
                meta["case_number"] = re.sub(r"\s+", " ", case_match.group(0)).strip().rstrip(".")

    meta["parties"] = extract_parties_from_lines(lines)

    hearing_match = _HEARING_RE.search(text)
    if hearing_match:
        meta["dates_of_hearing"] = re.sub(r"\s+", " ", hearing_match.group(1)).strip().rstrip(",")

    date_match = _DATE_RE.search(text)
    if date_match:
        meta["date"] = date_match.group(0).strip()

    meta["judge"] = extract_judge_from_lines(lines)

    return meta


# ----------------------------------------------------------------------
# MAIN pipeline for one PDF (non-streaming - batch_cli.py ke liye)
# ----------------------------------------------------------------------
def process_pdf(pdf_path, declared_court_type="SC"):
    lines = extract_lines(pdf_path)
    if not lines:
        return {"error": "No extractable text (likely scanned image PDF - needs OCR)"}

    cleaned_lines, boilerplate = remove_boilerplate(lines)

    first_page_text = " ".join(ln["text"] for ln in lines if ln["page"] == 1)
    metadata = extract_metadata(first_page_text, lines, declared_court_type=declared_court_type)

    chunks = build_chunks(cleaned_lines)

    for chunk in chunks:
        chunk["document_id"] = None
        chunk["source_file"] = os.path.basename(pdf_path)

    return {
        "source_file": os.path.basename(pdf_path),
        "metadata": metadata,
        "boilerplate_removed": boilerplate,
        "total_lines": len(lines),
        "total_chunks": len(chunks),
        "chunks": chunks,
    }


# ----------------------------------------------------------------------
# STREAMING version for API - har stage ke baad progress event yield
# karta hai, taake frontend real-time stageIndex update kar sake.
# api_server.py isko use karta hai.
# ----------------------------------------------------------------------
def process_pdf_stream(pdf_path, declared_court_type="SC"):
    """
    Generator hai - process_pdf() jaisa hi kaam karta hai lekin har
    major step ke baad ek dict yield karta hai:
        {"type": "progress", "stage_index": <int>, "stage_name": <str>}
    aur aakhir mein final result:
        {"type": "result", "data": <process_pdf() jaisa dict>}
    Agar error aaye to:
        {"type": "error", "detail": <str>}
    """
    yield {"type": "progress", "stage_index": 1, "stage_name": "parsing"}
    lines = extract_lines(pdf_path)
    if not lines:
        yield {"type": "error", "detail": "No extractable text (likely scanned image PDF - needs OCR)"}
        return

    yield {"type": "progress", "stage_index": 2, "stage_name": "chunking"}
    cleaned_lines, boilerplate = remove_boilerplate(lines)
    chunks = build_chunks(cleaned_lines)

    yield {"type": "progress", "stage_index": 3, "stage_name": "verifying"}
    first_page_text = " ".join(ln["text"] for ln in lines if ln["page"] == 1)
    metadata = extract_metadata(first_page_text, lines, declared_court_type=declared_court_type)

    for chunk in chunks:
        chunk["document_id"] = None
        chunk["source_file"] = os.path.basename(pdf_path)

    result = {
        "source_file": os.path.basename(pdf_path),
        "metadata": metadata,
        "boilerplate_removed": boilerplate,
        "total_lines": len(lines),
        "total_chunks": len(chunks),
        "chunks": chunks,
    }

    yield {"type": "result", "data": result}