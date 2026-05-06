"""
parse_income_tax.py
-------------------
Segments the "Income Tax Ordinance 2001" (FBR_Taxation_Document.pdf) into a
clean, hierarchical folder structure suitable for a RAG pipeline.

HOW IT WORKS
------------
* State-machine: tracks Chapter → Part → Division in real time, line-by-line.
* TOC guard: every body page starts with a running header like
    "Chapter III – Tax on Taxable Income ___________"
  The parser only starts tracking Chapter/Part/Division headings AFTER it sees
  this pattern for the first time, so all table-of-contents content is safely
  written to Introduction.txt instead of polluting chapter files.
* Full-line anchoring: CHAPTER / PART / DIVISION regexes require the heading
  to occupy the ENTIRE (trimmed) line, preventing mid-sentence matches like
  "Part IX of Chapter III".

OUTPUT LAYOUT
-------------
fbr_processed/
├── Introduction.txt               ← TOC + preamble (before body starts)
├── Chapter_1/
│   └── Chapter_1.txt              ← chapter content with no Parts
├── Chapter_3/
│   ├── Chapter_3.txt              ← content before the first Part
│   ├── Part_1/
│   │   └── Part_1.txt             ← Part content with no Divisions
│   └── Part_4/
│       ├── Part_4.txt             ← Part content before the first Division
│       ├── Division_1/
│       │   └── Division_1.txt
│       └── Division_2/
│           └── Division_2.txt
└── ...
"""

import os
import re
import shutil
import pdfplumber

PDF_PATH   = os.path.join(os.path.dirname(__file__), "FBR_Taxation_Document.pdf")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "fbr_processed")


# ─── Roman-numeral helpers ─────────────────────────────────────────────────────
_ROMAN_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE,
)
_ROMAN_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100,  "C"), (90,  "XC"), (50,  "L"), (40,  "XL"),
    (10,   "X"), (9,   "IX"), (5,   "V"), (4,   "IV"), (1, "I"),
]


def roman_to_int(s: str) -> int | None:
    """Return the integer value of a Roman numeral string, or None."""
    s = s.strip().upper()
    if not s or not _ROMAN_PATTERN.fullmatch(s):
        return None
    total, i = 0, 0
    for value, symbol in _ROMAN_VALUES:
        while s[i : i + len(symbol)] == symbol:
            total += value
            i += len(symbol)
            if i >= len(s):
                break
    return total if total > 0 else None


def parse_number(token: str) -> int | None:
    """Parse an Arabic or Roman numeral token; return None if unrecognised."""
    token = token.strip()
    if re.fullmatch(r"\d+", token):
        return int(token)
    return roman_to_int(token)


# ─── Regex patterns ────────────────────────────────────────────────────────────
# The number token accepts Roman-character sequences as well as Arabic digits.
_NUM = r"([IVXLCDMivxlcdm\d]+)"

# IMPORTANT: all three heading regexes are anchored at BOTH ends so they only
# match lines where the heading is the *entire* line content (after stripping).
RE_CHAPTER  = re.compile(rf"^CHAPTER\s+{_NUM}\s*$",  re.IGNORECASE)
RE_PART     = re.compile(rf"^PART\s+{_NUM}\s*$",     re.IGNORECASE)
RE_DIVISION = re.compile(rf"^DIVISION\s+{_NUM}\s*$", re.IGNORECASE)

# Running header that appears at the top/bottom of every body page, e.g.:
#   "Chapter III – Tax on Taxable Income ______________________"
#   "Chapter I – Preliminary__________________________________"
# Presence of this line means we have left the table of contents.
RE_RUNNING_HDR = re.compile(
    r"^Chapter\s+\S+\s*[\u2013\u2014\-\u2012–—]\s*.+_{3,}\s*$",
    re.IGNORECASE,
)

# Lines to discard silently (page numbers, watermarks, running-title footers).
RE_DISCARD = re.compile(
    r"^\s*("
    r"\d+\s*$"                       # bare page number
    r"|Income\s+Tax\s+Ordinance.*"   # "Income Tax Ordinance …" header/footer
    r"|FBR.*"                        # FBR watermark
    r"|www\.fbr\.gov\.pk.*"          # URL footer
    r")",
    re.IGNORECASE,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def clean_line(line: str) -> str:
    """Collapse internal whitespace runs and strip leading/trailing space."""
    return re.sub(r"[ \t]+", " ", line).strip()


def resolve_path(
    chapter:  int | None,
    part:     int | None,
    division: int | None,
) -> str:
    """
    Return the output file path for the given hierarchy position.
    Parent directories are created on demand.

    Mapping:
      (None,  None,  None ) → fbr_processed/Introduction.txt
      (N,     None,  None ) → fbr_processed/Chapter_N/Chapter_N.txt
      (N,     P,     None ) → fbr_processed/Chapter_N/Part_P/Part_P.txt
      (N,     P,     D    ) → fbr_processed/Chapter_N/Part_P/Division_D/Division_D.txt
      (N,     None,  D    ) → fbr_processed/Chapter_N/Division_D/Division_D.txt
                               (division directly under chapter, no part)
    """
    if chapter is None:
        return os.path.join(OUTPUT_DIR, "Introduction.txt")

    ch_dir = os.path.join(OUTPUT_DIR, f"Chapter_{chapter}")

    if part is None:
        if division is None:
            os.makedirs(ch_dir, exist_ok=True)
            return os.path.join(ch_dir, f"Chapter_{chapter}.txt")
        # Division directly under chapter (no intervening Part)
        dv_dir = os.path.join(ch_dir, f"Division_{division}")
        os.makedirs(dv_dir, exist_ok=True)
        return os.path.join(dv_dir, f"Division_{division}.txt")

    pt_dir = os.path.join(ch_dir, f"Part_{part}")

    if division is None:
        os.makedirs(pt_dir, exist_ok=True)
        return os.path.join(pt_dir, f"Part_{part}.txt")

    dv_dir = os.path.join(pt_dir, f"Division_{division}")
    os.makedirs(dv_dir, exist_ok=True)
    return os.path.join(dv_dir, f"Division_{division}.txt")


def write_line(
    line:     str,
    chapter:  int | None,
    part:     int | None,
    division: int | None,
) -> None:
    """Append *line* to the appropriate output file."""
    fpath = resolve_path(chapter, part, division)
    with open(fpath, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ─── Main parser ──────────────────────────────────────────────────────────────
def parse_pdf(pdf_path: str) -> None:
    # Always start with a clean slate.
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # State machine
    current_chapter:  int | None = None
    current_part:     int | None = None
    current_division: int | None = None

    # Guard: only parse headings once we are past the TOC / preamble.
    # Set to True the moment we see the first running-header line.
    in_body: bool = False

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"[INFO] Opened PDF — {total} pages")

        for page_num, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if not raw_text:
                continue

            for raw_line in raw_text.split("\n"):
                line = clean_line(raw_line)
                if not line:
                    continue

                # ── Running header: marks the start of body content ────────
                # Example: "Chapter III – Tax on Taxable Income ___________"
                # We set in_body = True and discard the line itself.
                if RE_RUNNING_HDR.match(line):
                    in_body = True
                    continue

                # ── Discard page numbers, watermarks, etc. ─────────────────
                if RE_DISCARD.match(line):
                    continue

                # ── Preamble (TOC / front matter) ──────────────────────────
                # Write verbatim to Introduction.txt without triggering any
                # state changes — this keeps TOC PART/DIVISION listings from
                # being mistaken for real headings.
                if not in_body:
                    write_line(line, None, None, None)
                    continue

                # ── CHAPTER heading ────────────────────────────────────────
                # Must be the entire trimmed line, e.g. "CHAPTER III"
                m_ch = RE_CHAPTER.match(line)
                if m_ch:
                    num = parse_number(m_ch.group(1))
                    if num is not None:
                        current_chapter  = num
                        current_part     = None
                        current_division = None
                        write_line(line, current_chapter, None, None)
                        continue

                # ── PART heading ───────────────────────────────────────────
                # Only recognised inside a chapter, e.g. "PART IV"
                m_pt = RE_PART.match(line)
                if m_pt and current_chapter is not None:
                    num = parse_number(m_pt.group(1))
                    if num is not None:
                        current_part     = num
                        current_division = None
                        write_line(line, current_chapter, current_part, None)
                        continue

                # ── DIVISION heading ───────────────────────────────────────
                # Only recognised inside a chapter, e.g. "Division I"
                m_dv = RE_DIVISION.match(line)
                if m_dv and current_chapter is not None:
                    num = parse_number(m_dv.group(1))
                    if num is not None:
                        current_division = num
                        write_line(line, current_chapter, current_part, current_division)
                        continue

                # ── Regular content line ───────────────────────────────────
                write_line(line, current_chapter, current_part, current_division)

            if page_num % 50 == 0:
                print(f"  … processed page {page_num}/{total}")

    print(f"\n[DONE] Files written to: {OUTPUT_DIR}\n")
    _print_tree(OUTPUT_DIR)


def _print_tree(root_dir: str) -> None:
    """Print a summary tree of the output directory."""
    total_files = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames.sort()
        level  = dirpath.replace(root_dir, "").count(os.sep)
        indent = "  " * level
        if level == 0:
            print(f"{root_dir}/")
        else:
            print(f"{indent}{os.path.basename(dirpath)}/")
        for fname in sorted(filenames):
            size = os.path.getsize(os.path.join(dirpath, fname))
            print(f"{indent}  {fname:<40s}  {size:>10,} bytes")
            total_files += 1
    print(f"\n[INFO] Total output files: {total_files}")


if __name__ == "__main__":
    parse_pdf(PDF_PATH)
