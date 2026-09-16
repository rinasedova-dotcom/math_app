# Extraction tools

Two reusable parsers for turning a problems+answers PDF pair into a
`data/<course-id>.json` file, one per known PDF layout. They use
`pdftotext -layout` plus layout-specific regexes; there is no generic parser
that works on arbitrary PDFs, so a new, third layout would need its own
script following the same pattern.

Both tools get the text and the answer key right automatically, but they
cannot see diagrams -- any question flagged in the "Manual review needed"
output still needs its image cropped by hand (see the root `README.md`) and
the placeholder `"image": "qN.png"` confirmed or removed.

## `parse_kangourou.py` -- THALES/Kangourou-style PDFs

One bilingual (English+Greek) problems PDF with inline `(A) ... (E) ...`
options, and one answers PDF with a single table holding every level
side-by-side (`LEVEL 1-2`, `LEVEL 3-4`, ... each with its own
QUESTION/ANSWER/POINTS columns).

```bash
python3 parse_kangourou.py problems.pdf answers.pdf \
  --level "LEVEL 5-6" \
  --id kangourou-YYYY-YYYY-level-5-6 \
  --name "Kangourou Mathematics YYYY-YYYY — Level 5-6" \
  --source "THALES Foundation – Kangourou Mathematics Competition YYYY-YYYY" \
  --image-path images/kangourou-YYYY-YYYY-level-5-6 \
  --out ../data/kangourou-YYYY-YYYY-level-5-6.json
```

## `parse_kmo.py` -- Cyprus Mathematical Society / Cyprus Math Olympiad PDFs

One problems PDF per grade, containing a full Greek edition followed by a
full "ENGLISH VERSION" edition (so no level/column choice is needed there --
just point it at the right grade's PDF). One separate answers PDF covers
every grade as columns in a table, with a flat points-per-correct-answer
score (given in the paper's instructions, not per question -- pass it with
`--points`).

```bash
python3 parse_kmo.py problems.pdf answers.pdf \
  --grade "5th & 6th grade" \
  --id kmo-YYYY-<grade-slug> \
  --name "Nth Cyprus Mathematical Olympiad YYYY — 5th & 6th Grade Primary" \
  --source "Cyprus Mathematical Society — ..." \
  --image-path images/kmo-YYYY-<grade-slug> \
  --points 4 \
  --out ../data/kmo-YYYY-<grade-slug>.json
```

## After running either one

1. Read the "Manual review needed" lines printed to stderr.
2. For each flagged question, open the source PDF at that question and
   decide: does it actually need a cropped diagram (crop it into
   `images/<course-id>/qN.png`, same technique as the existing courses --
   render the page with `pdftoppm`/PyMuPDF and crop the figure's bounding
   box), or was it a false positive (delete the `"image"` key)?
3. A `likely_has_formula` flag means pdftotext probably flattened a
   vertically-stacked fraction or multi-line equation into reading order
   and lost the structure (e.g. numerator then unrelated text then
   denominator) -- open the PDF and rewrite that question's `"text"` by
   hand.
4. Spot-check a handful of answers against the source answer key by eye,
   and against a plain computation where the question is a word problem --
   both parsers were validated this way against the two existing courses
   (and caught a few transcription mistakes in the original hand-built
   `data/*.json` files in the process: wrong points on two Kangourou
   questions, three wrong answers and a wrong points tier on the KMO one).
5. Add the new course to `../data/courses.json`.

## `pdf_common.py`

Shared helpers used by both parsers: running `pdftotext -layout`,
splitting pages, detecting Greek-script lines, stripping inline bilingual
asides (`"and/και 4"` -> `"and 4"`), locating a column in a space-aligned
(possibly multi-line-wrapped) table header, and the blank-line-run /
stacked-formula heuristics used to flag questions for manual review.
