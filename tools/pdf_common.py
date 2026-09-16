"""Shared helpers for extracting question data out of the two known
competition-PDF layouts (Kangourou/THALES and Cyprus Math Olympiad/CMS).

These PDFs are not parsed reliably by any single generic rule; what works is
`pdftotext -layout`, which preserves the on-page column positions as spaces,
plus a handful of layout-specific regexes. Nothing here reads pixels or
diagrams -- image cropping is still a manual/visual step (see crop_helper.py
and README.md for that part of the workflow).
"""
import re
import subprocess

GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")

# Map the Greek option letters used in the CMS/KMO papers onto plain A-E,
# since the site always renders plain Latin option labels.
GREEK_LETTER_TO_LATIN = {
    "Α": "A", "Β": "B", "Γ": "C", "Δ": "D", "Ε": "E",
}

# Some source PDFs have a stray Greek capital letter standing in for its
# Latin look-alike mid-sentence (e.g. an actual "Α father's age is..." in
# one CMS paper, where a Greek Alpha was typeset instead of a Latin A --
# almost certainly a font/typesetting slip in the source document, not
# something pdftotext introduces). These are easy to miss by eye because
# the glyphs render identically. Fix up single-letter "words" only, so a
# real Greek word elsewhere on an otherwise-English line is untouched.
_HOMOGLYPHS = str.maketrans({
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})
_LONE_GREEK_LETTER_RE = re.compile(r"\b[ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ]\b")


def fix_stray_greek_letters(s):
    return _LONE_GREEK_LETTER_RE.sub(lambda m: m.group().translate(_HOMOGLYPHS), s)


def run_pdftotext(pdf_path):
    """Return pdftotext -layout output as a single string."""
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def split_pages(text, header_lines=2, drop_trailing_blank_and_pagenum=True):
    """Split raw pdftotext -layout output on form-feeds into per-page line
    lists, stripping the repeated header lines and the trailing page-number
    line every page in these papers carries."""
    pages = []
    for chunk in text.split("\x0c"):
        lines = chunk.split("\n")
        if not lines or not "".join(lines).strip():
            continue
        lines = lines[header_lines:]
        if drop_trailing_blank_and_pagenum:
            while lines and (not lines[-1].strip() or lines[-1].strip().isdigit()):
                lines.pop()
        pages.append(lines)
    return pages


def is_greek_line(line):
    """True if a line is predominantly Greek-script text (so: skip it when
    building the English question text)."""
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    greek = sum(1 for c in letters if GREEK_RE.match(c))
    return greek / len(letters) > 0.4


_GREEK_ASIDE_RE = re.compile(
    r"/\s*(?:[Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿’΄]*[\s,.·→]*)+"
)


def strip_greek_asides(s):
    """Remove inline bilingual asides like 'and/και 4' -> 'and 4',
    '8 cm /εκ.' -> '8 cm', or a trailing '/ Νέα Υόρκη → Σικάγο' route
    aside, without touching non-Greek slashes (e.g. dates, fractions).
    Matches only ever start at a Greek character, so anything that matches
    is safe to blank out; replacing with a space (not '') keeps the words
    on either side from running together."""
    s = _GREEK_ASIDE_RE.sub(" ", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" .")
    # cosmetic: "33cm" -> "33 cm" (the source PDFs are inconsistent about
    # the space before a unit)
    s = re.sub(r"(\d)(cm|kg|mm|km)\b", r"\1 \2", s)
    # cosmetic: "4,5 cm" -> "4.5 cm" (European decimal comma in a Greek/Cypriot
    # source PDF, but the site's audience reads English-style decimals)
    return re.sub(r"(\d),(\d)", r"\1.\2", s)


def collapse_ws(s):
    return re.sub(r"\s+", " ", s).strip()


FRAGMENT_RE = re.compile(r"\S(?:[^\n]*?\S)?(?=\s{2,}|$)")


def find_column_range(header_lines, target_pattern):
    """Locate a column in a space-aligned, possibly multi-line-wrapped
    table header (as produced by `pdftotext -layout`).

    `header_lines` should be just the header block (the lines above the
    first data row). Lines that only contain one fragment (titles,
    captions) are ignored, since a real column header line always has
    multiple side-by-side fragments. Returns (x0, x1) character offsets
    that can be used to slice every data row with `line[x0:x1]`, or raises
    ValueError if `target_pattern` isn't found.
    """
    pattern = re.compile(target_pattern, re.IGNORECASE)
    frags = []
    for line in header_lines:
        line_frags = [(m.start(), m.group()) for m in FRAGMENT_RE.finditer(line) if m.group().strip()]
        if len(line_frags) >= 2:
            frags.extend(line_frags)

    matches = [x0 for x0, txt in frags if pattern.search(txt)]
    if not matches:
        raise ValueError(f"Column matching {target_pattern!r} not found in header")
    x0 = min(matches)
    right_candidates = sorted(rx for rx, _ in frags if rx > x0)
    x1 = right_candidates[0] if right_candidates else None
    return x0, x1


def iter_table_rows(lines, row_number_pattern=r"^\s*(\d+)\s"):
    """Yield (row_number, line) for lines that look like a numbered table
    row, stopping the header/data split cleanly."""
    for line in lines:
        m = re.match(row_number_pattern, line)
        if m:
            yield int(m.group(1)), line


def max_blank_run(lines):
    """Longest run of consecutive blank lines -- a rough signal that a
    diagram/image sat there in the original page (pdftotext -layout still
    reserves the image's vertical space as blank lines)."""
    best = cur = 0
    for line in lines:
        if not line.strip():
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


_BARE_FORMULA_LINE_RE = re.compile(r"^[\d\s×✕xX\+\-−.,=:/()]+$")


def likely_has_stacked_formula(lines):
    """True if a question block contains 2+ short symbols-only lines --
    typically the numerator/denominator of a vertically-stacked fraction
    or a multi-line equation, which pdftotext flattens into reading order
    and loses the '/' or alignment that made it a fraction. These need a
    manual look (usually a quick rewrite of the prompt text)."""
    hits = 0
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) <= 20 and _BARE_FORMULA_LINE_RE.match(stripped):
            hits += 1
    return hits >= 2
