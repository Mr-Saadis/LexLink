"""
LexLink - Unified Judgment PDF Pipeline
========================================
Ye file dono scripts (Supreme Court + LHC) ko MERGE karti hai taake ek hi
extraction script Supreme Court aur High Court, dono tarah ke judgments
pe consistently chale - bina is baat ki parwah kiye ke frontend se
"court_type" kya select kiya gaya tha.

Pipeline (har PDF ke liye same):
    extract lines (+ bbox)
        -> remove boilerplate (normalized, works for SC's exact-repeat
           footers AND HC's page-number-changing footers)
        -> fixed-window chunk (with overlap)
        -> best-effort metadata (SC-style regex tried first, HC-style
           regex tried as fallback, judge/dates extracted always)
        -> return dict (caller decides: save as JSON, or return as API
           response, or push to Qdrant/Supabase)

Is module ko do jagah use kiya jata hai:
    1. batch_cli.py   -> 4000+ PDFs ko offline, resumable, parallel process
                         karne ke liye
    2. api_server.py  -> "Select Files" button se upload hone wali single
                         PDF ko turant process karke response return karne
                         ke liye
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


# ----------------------------------------------------------------------
# STEP 1: Line-level extraction with bbox
# ----------------------------------------------------------------------
def extract_lines(pdf_path):
    """
    Har line ka: text, page number, bbox {x0,y0,x1,y1} nikalta hai.
    Yeh dono original scripts me identical tha, isliye unchanged.
    """
    doc = fitz.open(pdf_path)
    lines = []
    for page_num, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict")
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
                lines.append({
                    "text": text,
                    "page": page_num,
                    "bbox": {"x0": round(x0, 1), "y0": round(y0, 1),
                             "x1": round(x1, 1), "y1": round(y1, 1)}
                })
    doc.close()
    return lines


# ----------------------------------------------------------------------
# STEP 2: Boilerplate removal (MERGED - uses the more general HC logic)
# ----------------------------------------------------------------------
# Why the HC version wins over the SC version:
#   SC footers repeat EXACTLY across pages -> exact string match works.
#   LHC footers embed a changing page number, e.g. "W.P. No.10809/2008 2",
#   "W.P. No.10809/2008 3" -> exact match never repeats, footer survives
#   as noise in the chunks.
#   Normalizing away a trailing page number before comparing catches BOTH
#   cases: SC footers still repeat (nothing to strip), and LHC footers
#   now repeat too once the trailing number is stripped.
FOOTER_TRAIL_NUM = re.compile(r"\s*\d{1,4}\s*$")


def _normalize_for_boilerplate(text):
    return FOOTER_TRAIL_NUM.sub("", text).strip()


def remove_boilerplate(lines):
    norm_to_pages = {}
    for ln in lines:
        norm = _normalize_for_boilerplate(ln["text"])
        # Only multi-word lines are boilerplate candidates. Single common
        # words (the/and/is/by) can coincidentally repeat as their own
        # wrapped line on 3+ pages in a long document just by chance -
        # treating those as boilerplate would delete that word EVERYWHERE
        # it occurs, corrupting real sentences.
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
# STEP 4: Metadata extraction - MERGED (this is the actual fix you need)
# ----------------------------------------------------------------------
def _normalize_spaces(text):
    # PDF extraction sometimes yields non-breaking spaces (\xa0) instead
    # of plain " " - regex literals with a normal space won't match those.
    return re.sub(r"[\xa0\u2000-\u200b\u202f]", " ", text)


# ---- Court name: union of both scripts' patterns ----
_COURT_RE = re.compile(
    r"IN THE\s+(SUPREME COURT OF PAKISTAN|"
    r"LAHORE HIGH COURT|SINDH HIGH COURT|PESHAWAR HIGH COURT|"
    r"ISLAMABAD HIGH COURT|BALOCHISTAN HIGH COURT|"
    r"HIGH COURT OF[\w\s]+|[A-Z\s]+ TRIBUNAL)",
    re.IGNORECASE
)

# ---- Case number: SC style tried first, HC style as fallback ----
_CASE_NO_SC_RE = re.compile(
    r"((?:Civil|Criminal|Crl\.?|Const\.?|Writ|C\.?P\.?|W\.?P\.?)\s*"
    r"(?:Appeal|Petition|Application|Suit)?\s*No\.?\s*[\d/\-]+\s*(?:of\s*\d{4})?)",
    re.IGNORECASE
)
_CASE_NO_HC_RE = re.compile(
    r"Case No\.?:?\s*([A-Za-z\.\s]*?\d[\d/\-\.\s]*(?:of\s*\d{4})?)\s+[A-Z][a-z]",
    re.IGNORECASE
)

# ---- Parties: line-based (not blob-regex) ----
# IMPORTANT: full_text_first_page is built by joining PyMuPDF lines with a
# plain space (" ".join(...)), so real newline boundaries are lost. A
# blob-level regex like "[A-Z][\w\.\s&,]+?...Versus..." has no line
# boundary to stop at, so it can greedily swallow everything from the
# court header onwards (tested and confirmed - see note below). Searching
# LINE BY LINE (same trick already used for judge-name extraction) avoids
# this entirely, and naturally handles both layouts:
#   SC style: "Versus" sits alone on its own line, appellant name is the
#             line before it, respondent name is the line after
#   HC style: "X Versus Y" appears inline within a single line
_PARTY_SUFFIX_RE = re.compile(
    r"\s*(?:…|\.\.\.)?\s*(?:Appellant|Petitioner|Plaintiff|Respondent|Defendant)s?\s*\(?s?\)?\s*$",
    re.IGNORECASE
)
_PARTIES_INLINE_RE = re.compile(
    r"^([A-Z][\w\.\-\s&,]{2,80}?)\s+Versus\s+([A-Z][\w\.\-\s&,]{2,80}?)$",
    re.IGNORECASE
)


def extract_parties_from_lines(lines):
    norm_lines = [_normalize_spaces(ln["text"]).strip() for ln in lines]

    # Case A: "Versus" alone on its own line (common SC layout)
    for i, t in enumerate(norm_lines):
        if re.fullmatch(r"versus", t, re.IGNORECASE):
            if i - 1 >= 0 and i + 1 < len(norm_lines):
                appellant = _PARTY_SUFFIX_RE.sub("", norm_lines[i - 1]).strip()
                respondent = _PARTY_SUFFIX_RE.sub("", norm_lines[i + 1]).strip()
                if appellant and respondent:
                    return f"{appellant} vs {respondent}"

    # Case B: "X Versus Y" inline within a single line (common HC layout)
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
_JUDGE_NAME_RE = re.compile(r"^([A-Z][A-Za-z\.\s]{3,45}?),?\s*J\s*:-\s*$")
_JUDGE_SIG_RE = re.compile(r"^\(([A-Z][A-Za-z\.\s]{3,45}?)\)$")


def extract_judge_from_lines(lines):
    """
    Judge ka naam do jagah aata hai, har baar apni ALAG line pe:
      1. Opening line: "Syed Mansoor Ali Shah, J:-"
      2. Signature block: "(Syed Mansoor Ali Shah)" us ke agli line "Judge"
    Line-by-line search karte hain (joined paragraph pe nahi) taake
    counsel/officers ki preceding list is se na mix ho - kyunke newlines
    join hone ke baad koi punctuation boundary nahi bachta.
    """
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


def extract_metadata(full_text_first_page, lines):
    """
    Court-agnostic metadata extraction. SC-style regex pehle try hota hai
    (zyada specific / strict), agar match nahi mila to HC-style regex
    fallback ke taur pe try hota hai. Isi tarah ek hi function SC aur HC
    dono formats pe kaam karta hai - user ne dropdown me "SC" ya "HC"
    kuch bhi select kiya ho.
    """
    text = _normalize_spaces(full_text_first_page)

    meta = {
        "court": None,
        "case_number": None,
        "parties": None,
        "judge": None,
        "dates_of_hearing": None,
        "date": None,
    }

    court_match = _COURT_RE.search(text)
    if court_match:
        meta["court"] = re.sub(r"\s+", " ", court_match.group(0)).strip()

    case_match = _CASE_NO_SC_RE.search(text)
    if case_match:
        meta["case_number"] = re.sub(r"\s+", " ", case_match.group(0)).strip()
    else:
        case_match = _CASE_NO_HC_RE.search(text)
        if case_match:
            meta["case_number"] = re.sub(r"\s+", " ", case_match.group(1)).strip().rstrip(".")

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
# MAIN pipeline for one PDF - this is the single entry point both the
# batch CLI and the API server call
# ----------------------------------------------------------------------
def process_pdf(pdf_path, declared_court_type=None):
    """
    declared_court_type: jo user ne upload form me select kiya (e.g. "SC",
    "HC", "DC"). Sirf record/QA ke liye save hota hai - extraction logic
    ise use nahi karti, kyunke actual PDF format declared type se mismatch
    ho sakta hai (misfiled PDFs, scraper mixups, etc). Agar extraction
    khud detect kar le ke court kaunsa hai, wo alag se meta["court"] me
    hai.
    """
    lines = extract_lines(pdf_path)
    if not lines:
        return {"error": "No extractable text (likely scanned image PDF - needs OCR)"}

    cleaned_lines, boilerplate = remove_boilerplate(lines)

    first_page_text = " ".join(ln["text"] for ln in lines if ln["page"] == 1)
    metadata = extract_metadata(first_page_text, lines)
    metadata["court_type_declared"] = declared_court_type

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