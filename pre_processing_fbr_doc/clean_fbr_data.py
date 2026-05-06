"""
clean_fbr_data.py
-----------------
Cleans the text files inside fbr_processed/ by removing:

  1. Empty footnote-insertion markers  e.g.  5[ ]  3[ ]  1[ 2[ ] ]
  2. Inline numbered brackets           e.g.  4[sub-section] → sub-section
                                              1[;]            → ;
  3. Footnote explanation lines         e.g.  "Inserted by the Finance Act, 2025."
                                              "Full stop substituted by …"
                                              "Sub-section (4) omitted by …"
                                              "3 The word "company" substituted …"
  4. Quoted-omitted-text blocks         e.g.  text after "read as follows:" / "read as under:"
                                              that shows old (now-repealed) law in quotes
  5. Standalone bare footnote numbers   e.g.  a line containing only "1" or "3"
  6. Trailing/excessive blank lines     collapse 3+ consecutive blank lines → 1

The original data is NOT touched — it was already backed up to fbr_processed_original/.
"""

import os
import re

BASE       = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE, "fbr_processed")


# ── Patterns ──────────────────────────────────────────────────────────────────

# Matches empty footnote brackets:  5[ ]  5[]
RE_EMPTY_BRACKET = re.compile(r'\d+\[\s*\]')

# Matches innermost non-empty footnote bracket:  4[content]  (no nested brackets inside)
# [^\[\]] matches any char except [ and ] (including newlines in Python char classes)
RE_INNER_BRACKET = re.compile(r'\d+\[([^\[\]]*)\]')

# Presence of "Finance Act" (in any amendment-note context)
RE_FINANCE_ACT = re.compile(
    r'Finance\s+(?:Supplementary\s+)?Act',
    re.IGNORECASE,
)

# Amendment verb — indicates a footnote action
RE_AMEND_VERB = re.compile(
    r'\b(?:insert|substitut|omit|add|delet|amend|re.?numb|replac|re.?desig)\w*\b',
    re.IGNORECASE,
)

# Lines that are standalone amendment phrases even without "Finance Act"
RE_STANDALONE_FOOTNOTE = re.compile(
    r'^(?:'
    r'Full\s+stop\b|'                                  # "Full stop substituted …"
    r'Colon\b|'                                        # "Colon substituted …"
    r'Semi.?colon\b|'                                  # "Semi-colon substituted …"
    r'Re.?number(?:ed)?\b|'                            # "Re-numbered as …"
    r'Inserted\s+by\b|'                                # "Inserted by the Finance Act …"
    r'Substituted\s+(?:for|by)\b|'                     # "Substituted for … by …"
    r'Omitted\s+by\b|'                                 # "Omitted by Finance Act …"
    r'Added\s+by\b|'                                   # "Added by …"
    r'Deleted\s+by\b|'                                 # "Deleted by …"
    r'(?:The\s+)?(?:word|words|expression|figure|comma|bracket|dash|hyphen|apostrophe)'
    r'\s+.{0,80}(?:substitut|insert|omit|delet|amend|add)\w*\b'  # "The word … substituted"
    r')',
    re.IGNORECASE,
)

# Digit prefix + amendment phrase:  "3 Clause (7) omitted by …"
RE_DIGIT_FOOTNOTE = re.compile(
    r'^\d+\s+(?:Inserted|Substituted|Omitted|Added|Deleted|The\s+word|Words?\b|'
    r'The\s+expression|Clause\b|Sub.?section\b|Section\b|Proviso\b|'
    r'Re.?numb|Explanation\s+(?:added|inserted)|Note\b)',
    re.IGNORECASE,
)

# Triggers "read as follows" quoted-block mode
RE_READ_AS_FOLLOWS = re.compile(
    r'read\s+as\s+(?:follows|under)\s*[-:]*\s*$',
    re.IGNORECASE,
)

# Closing line of a quoted-omitted block (ends with a closing double-quote)
RE_QUOTE_CLOSE = re.compile(r'[""]\s*[;.,)]*\s*$')

# Date continuation line following a footnote split across lines
RE_DATE_CONTINUATION = re.compile(r'^dated\s+\d', re.IGNORECASE)

# Bare line that is only "follows:" or "under:" (footnote split across lines)
RE_FOLLOWS_ONLY = re.compile(r'^(?:follows|under)\s*[-:]+\s*$', re.IGNORECASE)

# Line that contains "Finance Act" plus a year — almost certainly part of a footnote
# even when the amendment verb is on the previous line
RE_FINANCE_ACT_YEAR = re.compile(r'Finance\s+(?:Supplementary\s+)?Act\W{0,5}20\d\d', re.IGNORECASE)

# Standalone bare integer
RE_BARE_INT = re.compile(r'^\d+$')


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_footnote_line(line: str) -> bool:
    """Return True if *line* is a footnote / amendment annotation to be removed."""
    # Rule 1: contains "Finance Act" AND an amendment verb
    if RE_FINANCE_ACT.search(line) and RE_AMEND_VERB.search(line):
        return True
    # Rule 2: starts with a standalone amendment phrase
    if RE_STANDALONE_FOOTNOTE.match(line):
        return True
    # Rule 3: starts with digit then amendment phrase
    if RE_DIGIT_FOOTNOTE.match(line):
        return True
    return False


def unwrap_brackets(text: str) -> str:
    """
    Remove all footnote-numbered bracket constructs from *text*.

    Pass 1: strip empty markers          N[ ] → ''
    Pass 2: iteratively unwrap content   N[content] → content
            (repeats until stable to handle nesting)
    """
    # Pass 1 — empty brackets
    text = RE_EMPTY_BRACKET.sub('', text)

    # Pass 2 — non-empty brackets (innermost first, up to 15 iterations)
    for _ in range(15):
        new = RE_INNER_BRACKET.sub(r'\1', text)
        if new == text:
            break
        text = new

    # Pass 3 — collapse multiple spaces left behind by empty-bracket removal
    # (preserve leading indentation by only collapsing mid-line runs)
    text = re.sub(r'(?<=\S) {2,}', ' ', text)

    return text


def remove_footnote_lines(text: str) -> str:
    """
    Remove footnote explanation lines and quoted-omitted-text blocks from *text*.
    Works line-by-line using a small state machine.
    """
    lines = text.split('\n')
    result: list[str] = []

    in_quoted_block  = False   # inside a "read as follows:" quoted-omission block
    prev_was_footnote = False  # previous non-blank line was a footnote

    for line in lines:
        stripped = line.strip()

        # ── Quoted-omission block ──────────────────────────────────────────
        if in_quoted_block:
            # The block ends when we see a closing double-quote at line end
            if RE_QUOTE_CLOSE.search(stripped):
                in_quoted_block = False
            # Also exit if we hit a line that is clearly new real content:
            # section number pattern like "18." or "15A." or a PART/DIVISION heading
            elif stripped and not stripped.startswith('"') and re.match(r'^\d+[A-Z]?\.\s+\S', stripped):
                in_quoted_block = False
                result.append(line)   # keep this real-content line
            continue  # skip everything inside the block

        # ── Blank line ─────────────────────────────────────────────────────
        if not stripped:
            result.append(line)
            continue

        # ── Continuation of previous footnote split across lines ───────────
        if prev_was_footnote:
            # "dated 30th June, 2020" — trailing date line
            if RE_DATE_CONTINUATION.match(stripped):
                continue
            # "follows:" or "under:" alone — the footnote sentence broke across lines
            if RE_FOLLOWS_ONLY.match(stripped):
                in_quoted_block = True
                continue

        # A line whose only Finance Act reference is a year (continuation of split footnote)
        if RE_FINANCE_ACT_YEAR.search(stripped) and not RE_AMEND_VERB.search(stripped):
            if prev_was_footnote:
                continue

        # ── Detect footnote line ───────────────────────────────────────────
        if is_footnote_line(stripped):
            prev_was_footnote = True
            if RE_READ_AS_FOLLOWS.search(stripped):
                in_quoted_block = True
            continue

        # ── Standalone bare footnote number ───────────────────────────────
        if RE_BARE_INT.match(stripped):
            prev_was_footnote = False
            continue

        # ── Normal content line ────────────────────────────────────────────
        prev_was_footnote = False
        result.append(line)

    return '\n'.join(result)


def collapse_blank_lines(text: str) -> str:
    """Collapse 3+ consecutive blank lines to a single blank line."""
    return re.sub(r'\n{3,}', '\n\n', text)


def clean_file(path: str) -> tuple[int, int]:
    """
    Clean a single .txt file in place.
    Returns (original_line_count, cleaned_line_count).
    """
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        original = fh.read()

    cleaned = unwrap_brackets(original)
    cleaned = remove_footnote_lines(cleaned)
    cleaned = collapse_blank_lines(cleaned)
    cleaned = cleaned.strip() + '\n'

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(cleaned)

    return original.count('\n'), cleaned.count('\n')


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not os.path.isdir(TARGET_DIR):
        print(f"[ERROR] Target directory not found: {TARGET_DIR}")
        return

    total_files = 0
    total_removed = 0

    for dirpath, _, filenames in os.walk(TARGET_DIR):
        for fname in sorted(filenames):
            if not fname.endswith('.txt'):
                continue
            fpath = os.path.join(dirpath, fname)
            rel   = os.path.relpath(fpath, TARGET_DIR)
            orig_lines, new_lines = clean_file(fpath)
            removed = orig_lines - new_lines
            total_files  += 1
            total_removed += removed
            print(f"  {rel:<60s}  -{removed:>5} lines")

    print(f"\n[DONE] Cleaned {total_files} files, removed {total_removed} lines total.")


if __name__ == "__main__":
    main()
