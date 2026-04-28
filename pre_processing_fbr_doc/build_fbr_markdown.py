"""
build_fbr_markdown.py
Reads fbr_processed_original/ and produces a single fbr_combined.md
ready for PageIndex tree index generation.

Pipeline:
  1. Walk directory → collect text from leaf-level files → assemble markdown with headings
  2. Parse all sections and build a section index (by section number, structural path, schedule name)
  3. Scan each section for cross-reference patterns; exclude self-references
  4. Resolve references → append inline blockquote summaries (max 5 per section)
  5. Write enriched markdown to fbr_combined.md

Usage:
    python build_fbr_markdown.py ./fbr_processed_original
    python build_fbr_markdown.py ./fbr_processed_original --output ./fbr_combined.md
    python build_fbr_markdown.py ./fbr_processed_original --no-validate
"""

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ─── Fallback chapter titles ──────────────────────────────────────────────────

CHAPTER_TITLES = {
    1:  "Preliminary",
    2:  "Charge to Tax",
    3:  "Tax on Taxable Income",
    4:  "Common Rules for Computation of Income",
    5:  "Deductions",
    6:  "Exemptions and Tax Concessions",
    7:  "Tax Credits",
    8:  "Minimum Tax",
    9:  "Tax Procedure",
    10: "Offences and Penalties",
    11: "Appeals",
    12: "Advance Rulings",
    13: "Schedules and Rules",
}

# ─── Enrichment constants ─────────────────────────────────────────────────────

ROMAN_TO_INT: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
}

SCHEDULE_ORDINALS: dict[str, int] = {
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
}

SCHEDULE_KEYS = {1: "first schedule", 2: "second schedule",
                 3: "third schedule", 4: "fourth schedule"}

MAX_REFS_PER_SECTION = 5
SUMMARY_MAX_CHARS = 300


# ─── Assembly helpers ─────────────────────────────────────────────────────────

def extract_number(name: str) -> int:
    match = re.search(r"(\d+)", name)
    return int(match.group(1)) if match else 0


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def read_file(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("Cannot read %s: %s", path, exc)
        return None
    text = clean_text(raw)
    if not text:
        log.warning("Empty file (skipped): %s", path)
        return None
    return text


def extract_title_from_text(text: str, fallback: str) -> str:
    lines = [l.strip() for l in text.splitlines()[:8] if l.strip()]
    header_pattern = re.compile(
        r"^(CHAPTER|PART|DIVISION|Division)\s+[IVXLCDM\d]+$",
        re.IGNORECASE,
    )
    for i, line in enumerate(lines):
        if header_pattern.match(line):
            if i + 1 < len(lines):
                candidate = lines[i + 1]
                if not header_pattern.match(candidate) and not re.match(r"^\d+[\.\(]", candidate):
                    return candidate.strip(".")
    return fallback


def extract_preamble(parent_text: str, first_child_text: str) -> str | None:
    if not first_child_text:
        return None
    child_lines = [l for l in first_child_text.splitlines() if l.strip()]
    header_pattern = re.compile(
        r"^(CHAPTER|PART|DIVISION|Division)\s+[IVXLCDM\d]+$", re.IGNORECASE
    )
    anchor_lines = [l for l in child_lines if not header_pattern.match(l.strip())]
    if not anchor_lines:
        return None
    anchor = anchor_lines[0][:150]
    pos = parent_text.find(anchor)
    if pos == -1:
        return None
    preamble = parent_text[:pos].strip()
    preamble_lines = preamble.splitlines()
    while preamble_lines and header_pattern.match(preamble_lines[0].strip()):
        preamble_lines.pop(0)
    if preamble_lines:
        preamble_lines.pop(0)
    preamble = "\n".join(preamble_lines).strip()
    return preamble if preamble else None


def get_subdirs(folder: Path, prefix: str) -> list[Path]:
    if not folder.is_dir():
        return []
    dirs = [d for d in folder.iterdir() if d.is_dir() and d.name.startswith(prefix)]
    return sorted(dirs, key=lambda d: extract_number(d.name))


def get_txt_files(folder: Path) -> list[Path]:
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix == ".txt"]
    return sorted(files, key=lambda f: extract_number(f.stem))


# ─── Enrichment helpers ───────────────────────────────────────────────────────

def _roman_to_int(s: str) -> int | None:
    return ROMAN_TO_INT.get(s.upper())


def _normalize_num(s: str) -> int | None:
    """Accept arabic digit string or Roman numeral, return int or None."""
    if re.fullmatch(r"\d+", s):
        return int(s)
    return _roman_to_int(s)


def _parse_block(block: str) -> tuple[str, str]:
    """Split 'heading\\n\\ncontent' → (heading_line, content_body)."""
    idx = block.find("\n")
    if idx == -1:
        return block, ""
    return block[:idx], block[idx:].lstrip("\n")


def _find_defined_section_nums(content: str) -> set[str]:
    """
    Return the set of section numbers *defined* in this content block,
    e.g. {"2", "12", "12A"}.
    Pattern: line starts with NNN. or NNNx. followed by a letter (section header).
    """
    defined: set[str] = set()
    for m in re.finditer(r"^(\d+[A-Z]?)\.\s+[A-Za-z]", content, re.MULTILINE):
        defined.add(m.group(1))
    return defined


def build_section_index(blocks: list[str]) -> dict[str, dict]:
    """
    Build a lookup dict from canonical reference key → section entry dict.

    Keys registered per block:
      • "section N" / "section NA"  for every section number defined in the content
      • "chapter N"                 from heading like "## Chapter N — …"
      • "part N"                    from heading like "### Part N — …"  (first-seen wins)
      • "division N"                from heading like "#### Division N — …" (first-seen wins)
      • "first/second/… schedule"   detected from heading title keywords
    """
    index: dict[str, dict] = {}

    for block in blocks:
        heading, content = _parse_block(block)
        if not heading.startswith("#"):
            continue

        level = len(heading) - len(heading.lstrip("#"))
        heading_title = heading.lstrip("#").strip()   # e.g. "Chapter 3 — Tax on Taxable Income"
        heading_title_lower = heading_title.lower()

        defined_nums = _find_defined_section_nums(content)

        entry = {
            "heading": heading,
            "heading_title": heading_title,
            "content": content,
            "heading_level": level,
            "defined_nums": defined_nums,
        }

        # Register structural keys
        chap_m = re.match(r"Chapter\s+(\d+)", heading_title, re.IGNORECASE)
        part_m = re.match(r"Part\s+(\d+)", heading_title, re.IGNORECASE)
        div_m  = re.match(r"Division\s+(\d+)", heading_title, re.IGNORECASE)

        if chap_m:
            index[f"chapter {chap_m.group(1)}"] = entry
        if part_m:
            index.setdefault(f"part {part_m.group(1)}", entry)
        if div_m:
            index.setdefault(f"division {div_m.group(1)}", entry)

        # Register every section number defined here
        for num in defined_nums:
            index.setdefault(f"section {num.lower()}", entry)

        # Register schedule name keys
        for word, sched_num in SCHEDULE_ORDINALS.items():
            if f"{word} schedule" in heading_title_lower:
                sched_key = SCHEDULE_KEYS[sched_num]
                index.setdefault(sched_key, entry)
                break

        # Heuristic: Chapter 13 Parts → schedule names by position
        if "chapter 13" in heading_title_lower:
            pass  # handled above via heading title keywords
        # Fallback: detect "rates of tax" → first schedule
        if "rates of tax" in heading_title_lower and level == 3:
            index.setdefault("first schedule", entry)
        if ("reduction in tax" in heading_title_lower or "exemption" in heading_title_lower) and level == 3:
            index.setdefault("second schedule", entry)
        if ("deduction of tax at source" in heading_title_lower or "depreciation" in heading_title_lower) and level == 3:
            index.setdefault("third schedule", entry)

    return index


def _extract_cross_refs(content: str, defined_nums: set[str]) -> list[tuple[str, str]]:
    """
    Scan content for cross-reference patterns.
    Returns list of (canonical_key, display_name) — deduplicated, self-refs excluded.

    canonical_key: "section 149", "chapter 3", "first schedule", "part 1", "division 2"
    display_name:  "Section 149", "Chapter 3", "First Schedule", "Part 1", "Division 2"
    """
    found: dict[str, str] = {}   # canonical_key → display_name (preserves first display)

    # ── Schedule references (highest priority — catch before generic section scan) ──
    for m in re.finditer(
        r"\b(First|Second|Third|Fourth|1st|2nd|3rd|4th)\s+Schedule\b",
        content, re.IGNORECASE
    ):
        word = m.group(1).lower()
        sched_num = SCHEDULE_ORDINALS.get(word)
        if sched_num:
            key = SCHEDULE_KEYS[sched_num]
            found.setdefault(key, key.title())

    # ── "the Schedule" — too generic, skip ──

    # ── "clause (X) of section N" — capture section number ──
    for m in re.finditer(
        r"\b[Cc]lauses?\s+\(\w+\)\s+of\s+[Ss]ections?\s+(\d+[A-Z]?)",
        content
    ):
        num = m.group(1)
        if num not in defined_nums:
            key = f"section {num.lower()}"
            found.setdefault(key, f"Section {num}")

    # ── "sub-section (N) of section M" — capture section M ──
    for m in re.finditer(
        r"\b[Ss]ub-?[Ss]ection\s+\(\d+\)\s+of\s+[Ss]ections?\s+(\d+[A-Z]?)",
        content
    ):
        num = m.group(1)
        if num not in defined_nums:
            key = f"section {num.lower()}"
            found.setdefault(key, f"Section {num}")

    # ── "Section N" / "Sections N" ──
    for m in re.finditer(r"\b[Ss]ections?\s+(\d+[A-Z]?)", content):
        num = m.group(1)
        if num not in defined_nums:
            key = f"section {num.lower()}"
            found.setdefault(key, f"Section {num}")

    # ── "Part I/1 of the X Schedule" — resolve to schedule key ──
    for m in re.finditer(
        r"\b[Pp]art\s+([IVX]+|\d+)\s+of\s+the\s+(\w+)\s+[Ss]chedule\b",
        content
    ):
        sched_word = m.group(2).lower()
        sched_num = SCHEDULE_ORDINALS.get(sched_word)
        if sched_num:
            key = SCHEDULE_KEYS[sched_num]
            found.setdefault(key, key.title())
        else:
            # Fall through to generic Part reference
            n = _normalize_num(m.group(1))
            if n:
                key = f"part {n}"
                found.setdefault(key, f"Part {n}")

    # ── "Part I/1" (standalone) ──
    for m in re.finditer(r"\b[Pp]art\s+([IVX]+|\d+)\b", content):
        n = _normalize_num(m.group(1))
        if n:
            key = f"part {n}"
            found.setdefault(key, f"Part {n}")

    # ── "Division I/1" ──
    for m in re.finditer(r"\b[Dd]ivision\s+([IVX]+|\d+)\b", content):
        n = _normalize_num(m.group(1))
        if n:
            key = f"division {n}"
            found.setdefault(key, f"Division {n}")

    # Exclude any key that maps back to a section defined in this block
    result = []
    for key, display in found.items():
        if key.startswith("section "):
            num = key[len("section "):].upper()
            if num in defined_nums or num.lower() in defined_nums:
                continue
        result.append((key, display))

    return result


def _trim_to_sentence(text: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    """Return up to max_chars of text, trimmed to the last sentence boundary."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Find rightmost sentence-ending punctuation
    last = max(chunk.rfind("."), chunk.rfind("!"), chunk.rfind("?"))
    if last > max_chars // 4:   # ensure we don't trim too aggressively
        return chunk[:last + 1]
    return chunk


def _ref_priority(key: str, entry: dict) -> int:
    """Lower = higher priority. Used to rank refs when > MAX_REFS_PER_SECTION."""
    if "schedule" in key:
        return 1
    if key.startswith("division"):
        return 1
    htitle = entry.get("heading_title", "").lower()
    if "chapter 6" in htitle or "exemption" in htitle or "concession" in htitle:
        return 2
    if "chapter 7" in htitle or "international" in htitle:
        return 2
    if "chapter 3" in htitle or "chapter 4" in htitle:
        return 3
    if key == "section 2":
        return 5   # definitions — deprioritize
    return 4


def _format_ref_block(resolved: list[tuple[str, str, str]]) -> str:
    """
    resolved: list of (display_name, heading_title, summary_text)
    Returns a blockquote reference block as a markdown string.
    """
    lines = ["\n---", "> **Referenced Sections:**", ">"]
    for display, htitle, summary in resolved:
        # Strip leading chapter/part/division prefix from htitle for cleaner display
        # e.g. "Chapter 3 — Tax on Taxable Income" → "Tax on Taxable Income"
        short_title = re.sub(r"^(Chapter|Part|Division)\s+\d+\s*[—\-]\s*", "", htitle, flags=re.IGNORECASE).strip()
        label = f"{display} ({short_title})" if short_title and short_title != htitle else display
        # Wrap summary lines in blockquote
        summary_escaped = summary.replace("\n", " ").strip()
        lines.append(f"> **{label}:** {summary_escaped}")
        lines.append(">")
    lines.append("---")
    return "\n".join(lines)


def enrich_blocks(
    blocks: list[str],
    section_index: dict[str, dict],
) -> tuple[list[str], dict]:
    """
    Enrich each section block with a cross-reference summary block.
    Returns (enriched_blocks, stats_dict).
    """
    stats = {
        "total_processed": 0,
        "sections_with_refs": 0,
        "total_found": 0,
        "total_resolved": 0,
        "total_unresolved": 0,
        "skipped_self": 0,
        "skipped_sec2": 0,
        "heading_crossrefs": {},   # heading_line → count of refs added
    }

    enriched: list[str] = []

    for block in blocks:
        heading, content = _parse_block(block)

        # Only enrich blocks that have actual content
        if not content.strip() or not heading.startswith("#"):
            enriched.append(block)
            continue

        stats["total_processed"] += 1

        defined_nums = _find_defined_section_nums(content)
        raw_refs = _extract_cross_refs(content, defined_nums)
        stats["total_found"] += len(raw_refs)

        # Count self-references excluded (already done in _extract_cross_refs,
        # but track them here for stats by comparing raw extraction before filtering)
        raw_refs_unfiltered_count = len(raw_refs)  # already filtered

        # Resolve each ref against the index
        resolvable: list[tuple[str, str, dict]] = []   # (key, display, entry)
        for key, display in raw_refs:
            entry = section_index.get(key)
            if entry is None:
                stats["total_unresolved"] += 1
                continue
            # Skip if this entry IS the current section (self-reference via index)
            if entry["heading"] == heading:
                stats["skipped_self"] += 1
                continue
            resolvable.append((key, display, entry))
            stats["total_resolved"] += 1

        if not resolvable:
            enriched.append(block)
            stats["heading_crossrefs"][heading] = 0
            continue

        # Sort by priority
        resolvable.sort(key=lambda t: _ref_priority(t[0], t[2]))

        # Apply Section 2 deprioritization: count how many non-sec2 refs we have
        non_sec2 = [t for t in resolvable if t[0] != "section 2"]
        sec2     = [t for t in resolvable if t[0] == "section 2"]

        if len(non_sec2) >= MAX_REFS_PER_SECTION:
            # Drop all Section 2 refs
            stats["skipped_sec2"] += len(sec2)
            selected = non_sec2[:MAX_REFS_PER_SECTION]
        else:
            remaining_slots = MAX_REFS_PER_SECTION - len(non_sec2)
            stats["skipped_sec2"] += max(0, len(sec2) - remaining_slots)
            selected = non_sec2 + sec2[:remaining_slots]

        # Deduplicate selected by heading (different keys may resolve to same entry)
        seen_headings: set[str] = set()
        deduped: list[tuple[str, str, dict]] = []
        for key, display, entry in selected:
            if entry["heading"] not in seen_headings:
                seen_headings.add(entry["heading"])
                deduped.append((key, display, entry))
        selected = deduped[:MAX_REFS_PER_SECTION]

        # Build resolved list for formatting
        resolved_fmt: list[tuple[str, str, str]] = []
        for key, display, entry in selected:
            summary = _trim_to_sentence(entry["content"], SUMMARY_MAX_CHARS)
            resolved_fmt.append((display, entry["heading_title"], summary))

        ref_block = _format_ref_block(resolved_fmt)
        enriched_block = f"{heading}\n\n{content}{ref_block}"
        enriched.append(enriched_block)

        count = len(selected)
        stats["sections_with_refs"] += 1
        stats["heading_crossrefs"][heading] = count

    return enriched, stats


# ─── Assembler ────────────────────────────────────────────────────────────────

class Assembler:
    def __init__(self, root: Path, output: Path):
        self.root = root
        self.output = output
        self.sections: list[str] = []
        self.summary_lines: list[str] = []
        self.stats = {
            "introduction": 0,
            "chapters": 0,
            "parts": 0,
            "divisions": 0,
            "total_chars": 0,
        }

    def _emit(self, heading: str, content: str | None, indent: str, note: str):
        self.summary_lines.append(f"{indent}{heading}  [{note}]")
        if content:
            self.sections.append(f"{heading}\n\n{content}")
            self.stats["total_chars"] += len(content)
        else:
            self.sections.append(heading)

    def process_division(self, div_dir: Path, heading_prefix: str):
        num = extract_number(div_dir.name)
        txts = get_txt_files(div_dir)
        if not txts:
            log.warning("No .txt in division folder: %s", div_dir)
            return
        texts = [read_file(f) for f in txts]
        texts = [t for t in texts if t]
        if not texts:
            return
        combined = "\n\n".join(texts)
        title = extract_title_from_text(combined, f"Division {num}")
        heading = f"{heading_prefix} Division {num} — {title}"
        self._emit(heading, combined, "        ", f"leaf — used {div_dir.name}.txt")
        self.stats["divisions"] += 1

    def process_part(self, part_dir: Path, heading_prefix: str):
        num = extract_number(part_dir.name)
        part_txt_path = part_dir / f"{part_dir.name}.txt"
        part_text = read_file(part_txt_path) if part_txt_path.exists() else None
        title_fallback = f"Part {num}"
        title = extract_title_from_text(part_text, title_fallback) if part_text else title_fallback
        heading = f"{heading_prefix} Part {num} — {title}"
        div_dirs = get_subdirs(part_dir, "Division_")
        if not div_dirs:
            self._emit(heading, part_text, "      ", f"leaf — used {part_dir.name}.txt")
            self.stats["parts"] += 1
            return
        preamble = None
        if part_text:
            first_div_txt = get_txt_files(div_dirs[0])
            first_div_text = read_file(first_div_txt[0]) if first_div_txt else None
            if first_div_text:
                preamble = extract_preamble(part_text, first_div_text)
        self._emit(heading, preamble, "      ", "has children — preamble only")
        self.stats["parts"] += 1
        for div_dir in div_dirs:
            self.process_division(div_dir, "####")

    def process_chapter(self, chap_dir: Path):
        num = extract_number(chap_dir.name)
        chap_txt_path = chap_dir / f"{chap_dir.name}.txt"
        chap_text = read_file(chap_txt_path) if chap_txt_path.exists() else None
        title_fallback = CHAPTER_TITLES.get(num, f"Chapter {num}")
        title = extract_title_from_text(chap_text, title_fallback) if chap_text else title_fallback
        heading = f"## Chapter {num} — {title}"
        part_dirs = get_subdirs(chap_dir, "Part_")
        if not part_dirs:
            self._emit(heading, chap_text, "    ", f"leaf — used {chap_dir.name}.txt")
            self.stats["chapters"] += 1
            return
        preamble = None
        if chap_text:
            first_part_dir = part_dirs[0]
            first_part_txt = first_part_dir / f"{first_part_dir.name}.txt"
            first_part_text = read_file(first_part_txt) if first_part_txt.exists() else None
            if first_part_text:
                preamble = extract_preamble(chap_text, first_part_text)
        self._emit(heading, preamble, "    ", "has children — preamble only")
        self.stats["chapters"] += 1
        for part_dir in part_dirs:
            self.process_part(part_dir, "###")

    def run(self):
        # ── Step 1: Assembly ──────────────────────────────────────────────────
        self.sections.append("# Income Tax Ordinance 2001")
        self.summary_lines.append("  # Income Tax Ordinance 2001")

        intro_path = self.root / "Introduction.txt"
        if intro_path.exists():
            intro_text = read_file(intro_path)
            if intro_text:
                self.sections.append(intro_text)
                self.stats["introduction"] = 1
                self.stats["total_chars"] += len(intro_text)
                self.summary_lines.append("    [Introduction.txt included]")

        chap_dirs = get_subdirs(self.root, "Chapter_")
        for chap_dir in chap_dirs:
            self.process_chapter(chap_dir)

        # ── Step 2: Build section index ───────────────────────────────────────
        print("Building section index...", flush=True)
        section_index = build_section_index(self.sections)
        print(f"  Index built: {len(section_index)} keys registered.", flush=True)

        # ── Step 3 & 4: Scan + enrich ─────────────────────────────────────────
        print("Enriching sections with cross-reference summaries...", flush=True)
        self.sections, enrich_stats = enrich_blocks(self.sections, section_index)

        # Update summary lines: replace note for leaf sections with cross-ref count
        crossrefs_by_heading = enrich_stats["heading_crossrefs"]
        updated_summary: list[str] = []
        for sline in self.summary_lines:
            replaced = False
            for heading, count in crossrefs_by_heading.items():
                short = heading.lstrip("#").strip()
                if short and short in sline and "[leaf —" in sline:
                    label = "0 cross-refs" if count == 0 else f"{count} cross-refs added"
                    sline = re.sub(r"\[leaf — .*?\]", f"[leaf — {label}]", sline)
                    replaced = True
                    break
            updated_summary.append(sline)
        self.summary_lines = updated_summary

        # ── Write output ──────────────────────────────────────────────────────
        final_md = "\n\n".join(self.sections) + "\n"
        self.output.write_text(final_md, encoding="utf-8")

        # ── Print summary ─────────────────────────────────────────────────────
        total_sections = (
            self.stats["introduction"]
            + self.stats["chapters"]
            + self.stats["parts"]
            + self.stats["divisions"]
        )
        print("\n=== FBR Markdown Assembly + Enrichment Complete ===\n")
        print("Structure built:")
        for line in self.summary_lines:
            print(line)
        print(
            f"\nSections: {total_sections} total "
            f"({self.stats['chapters']} chapters, "
            f"{self.stats['parts']} parts, "
            f"{self.stats['divisions']} divisions, "
            f"{self.stats['introduction']} introduction)"
        )

        # Enrichment stats
        resolved   = enrich_stats["total_resolved"]
        unresolved = enrich_stats["total_unresolved"]
        total_ref  = resolved + unresolved
        pct = f"{resolved / total_ref * 100:.1f}%" if total_ref > 0 else "N/A"
        print(f"\nEnrichment stats:")
        print(f"  Total sections processed:       {enrich_stats['total_processed']}")
        print(f"  Sections with cross-references: {enrich_stats['sections_with_refs']}")
        print(f"  Total cross-references found:   {enrich_stats['total_found']}")
        print(f"  Cross-references resolved:      {resolved} ({pct})")
        print(f"  Cross-references unresolved:    {unresolved} ({100 - float(pct.rstrip('%')):.1f}% of found)" if total_ref > 0 else "  Cross-references unresolved:    0")
        print(f"  Skipped (self-references):      {enrich_stats['skipped_self']}")
        print(f"  Skipped (Section 2, over limit):{enrich_stats['skipped_sec2']}")

        file_size_kb = self.output.stat().st_size // 1024
        print(f"\nOutput: {self.output}")
        print(f"Total file size: ~{file_size_kb:,} KB")

        return final_md


# ─── Validation ───────────────────────────────────────────────────────────────

def validate(md_text: str):
    lines = md_text.splitlines()
    heading_lines = [(i, line) for i, line in enumerate(lines) if line.startswith("#")]

    print("\n=== Validation ===\n")

    # 1. Heading hierarchy check
    prev_level = 0
    hierarchy_ok = True
    for i, (ln, heading) in enumerate(heading_lines):
        level = len(heading) - len(heading.lstrip("#"))
        if level > prev_level + 1:
            print(
                f"  WARNING: Heading level skipped at line {ln + 1}: "
                f"'{heading[:60]}' (jumped from level {prev_level} to {level})"
            )
            hierarchy_ok = False
        prev_level = level
    if hierarchy_ok:
        print("  [OK] Heading hierarchy is valid — no levels skipped.")

    # 2. Empty section check (excluding sections that are parent containers)
    empty_sections = []
    for i in range(len(heading_lines) - 1):
        ln_cur, h_cur = heading_lines[i]
        ln_next, _    = heading_lines[i + 1]
        between = [l for l in lines[ln_cur + 1:ln_next] if l.strip()]
        if not between:
            empty_sections.append(f"    line {ln_cur + 1}: '{h_cur[:70]}'")
    if empty_sections:
        print(f"  WARNING: {len(empty_sections)} empty section(s):")
        for s in empty_sections[:10]:
            print(s)
        if len(empty_sections) > 10:
            print(f"    ... and {len(empty_sections) - 10} more")
    else:
        print("  [OK] No empty sections found.")

    # 3. Duplicate content check (50-char mid-body sample)
    section_texts = []
    for i, (ln, heading) in enumerate(heading_lines):
        next_ln = heading_lines[i + 1][0] if i + 1 < len(heading_lines) else len(lines)
        body = "\n".join(lines[ln + 1:next_ln]).strip()
        section_texts.append((heading[:60], body))

    duplicates_found = 0
    for i, (h1, body1) in enumerate(section_texts):
        if len(body1) < 100:
            continue
        mid = len(body1) // 2
        sample = body1[mid:mid + 50].strip()
        if len(sample) < 20:
            continue
        for j, (h2, body2) in enumerate(section_texts):
            if j <= i:
                continue
            if sample in body2:
                print(
                    f"  WARNING: Possible duplicate content between:\n"
                    f"    [{i}] {h1}\n"
                    f"    [{j}] {h2}\n"
                    f"    Sample: '{sample[:40]}'"
                )
                duplicates_found += 1
                if duplicates_found >= 5:
                    print("  (Stopped after 5 duplicate warnings)")
                    break
        if duplicates_found >= 5:
            break
    if duplicates_found == 0:
        print("  [OK] No duplicate content detected.")

    # 4. Heading counts
    counts: dict[int, int] = {}
    for _, heading in heading_lines:
        level = len(heading) - len(heading.lstrip("#"))
        counts[level] = counts.get(level, 0) + 1
    print(f"\n  Heading counts:")
    for level in sorted(counts):
        print(f"    {'#' * level}  →  {counts[level]}")

    # 5. Cross-reference block check
    ref_blocks = md_text.count("> **Referenced Sections:**")
    print(f"\n  Cross-reference blocks inserted: {ref_blocks}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Assemble and enrich FBR Income Tax Ordinance into a single markdown file."
    )
    parser.add_argument("source", help="Path to fbr_processed_original/ directory")
    parser.add_argument(
        "--output", default="fbr_combined.md",
        help="Output file path (default: fbr_combined.md)"
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip the validation step"
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"ERROR: Source directory not found: {source}", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output).resolve()
    assembler = Assembler(source, output)
    md_text = assembler.run()

    if not args.no_validate:
        validate(md_text)


if __name__ == "__main__":
    main()
