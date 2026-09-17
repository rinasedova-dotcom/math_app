"""Parser for the THALES/Kangourou-style competition PDFs: a single
bilingual (English + Greek) problems PDF with inline "(A) ... (E) ..."
options, and a single answers PDF with one "LEVEL x-y" table holding every
level side by side as repeated QUESTION/ANSWER/POINTS column groups.

Usage:
    python3 parse_kangourou.py problems.pdf answers.pdf --level "LEVEL 5-6" --out data/course-id.json \
        --id course-id --name "Display name" --source "Where this is from" --image-path images/course-id
"""
import argparse
import json
import re
import sys

from pdf_common import (
    run_pdftotext, split_pages, is_greek_line, strip_greek_asides,
    collapse_ws, max_blank_run, fix_stray_greek_letters, likely_has_stacked_formula,
    GREEK_LETTER_TO_LATIN,
)

# A handful of years render the ordered-list marker as a stray symbol
# before the number ("# 1." instead of "1." -- likely a symbol-font
# bullet pdftotext couldn't map), so that lone leading glyph is optional.
QUESTION_START_RE = re.compile(r"^\s{0,4}[^\w\s]?\s*(\d{1,2})\.\s*(.*)$")
# Most years use plain "(A) ... (E)"; a few (2023, 2023-2024) use Greek
# option letters in parens instead, "(Α) ... (Ε)", occasionally mixed with
# a stray Latin letter in the same line (a typesetting slip, not a format
# switch) -- so accept either alphabet per option, not per file.
_OPTION_LETTERS = "A-EΑΒΓΔΕ"
OPTION_LINE_START_RE = re.compile(rf"^\([{_OPTION_LETTERS}]\)")
OPTION_TOKEN_RE = re.compile(rf"\(([{_OPTION_LETTERS}])\)\s*([^()]*?)(?=\s*\([{_OPTION_LETTERS}]\)|$)")


def _normalize_label(label):
    return GREEK_LETTER_TO_LATIN.get(label, label)


def parse_problems(pdf_path):
    """Return a list of dicts: {number, text, options, needs_image_options,
    likely_has_diagram}."""
    raw = run_pdftotext(pdf_path)
    pages = split_pages(raw)

    all_lines = []
    for page in pages:
        all_lines.extend(page)
        all_lines.append("")  # keep a page-boundary gap for the blank-run heuristic

    raw_starts = []
    for i, line in enumerate(all_lines):
        m = QUESTION_START_RE.match(line)
        if m:
            raw_starts.append((i, int(m.group(1)), m.group(2)))

    # Question numbers must increase strictly by 1; anything else is a
    # false positive (e.g. a sentence that happens to wrap onto a new line
    # right after "...is always 7. The next sentence...") and gets folded
    # back into the question it actually belongs to.
    starts = []
    expected = 1
    for item in raw_starts:
        if item[1] == expected:
            starts.append(item)
            expected += 1
    questions = []
    for idx, (line_i, qnum, first_line_rest) in enumerate(starts):
        end_i = starts[idx + 1][0] if idx + 1 < len(starts) else len(all_lines)
        block = [first_line_rest] + all_lines[line_i + 1:end_i]

        diagram_signal = max_blank_run(block) >= 4
        formula_signal = likely_has_stacked_formula(block)

        # Strip inline bilingual asides ("and/και", "8 cm /εκ.") before the
        # Greek-line filter, otherwise an options line with several such
        # asides can look majority-Greek by character count and get
        # dropped whole.
        cleaned = [strip_greek_asides(l) if OPTION_LINE_START_RE.match(l.strip()) or l.strip().startswith("(") else l for l in block]
        kept = [l for l in cleaned if l.strip() and not is_greek_line(l)]

        option_line_idxs = [i for i, l in enumerate(kept) if OPTION_LINE_START_RE.match(l.strip())]
        prompt_lines = kept[: option_line_idxs[0]] if option_line_idxs else kept
        prompt = fix_stray_greek_letters(collapse_ws(" ".join(prompt_lines)))

        options = []
        if option_line_idxs:
            option_lines = kept[option_line_idxs[0]:]
            for oline in option_lines:
                found = OPTION_TOKEN_RE.findall(oline)
                if len(found) > 1:
                    for label, text in found:
                        options.append({"label": _normalize_label(label), "text": strip_greek_asides(text)})
                elif len(found) == 1:
                    label, _text = found[0]
                    # a lone "(X) ..." line -- text may run to end of line
                    text = re.sub(rf"^\([{_OPTION_LETTERS}]\)\s*", "", oline.strip())
                    options.append({"label": _normalize_label(label), "text": strip_greek_asides(text)})
        needs_image_options = len(options) < 5
        if needs_image_options:
            options = [{"label": chr(ord("A") + i), "text": ""} for i in range(5)]

        questions.append({
            "number": qnum,
            "text": prompt,
            "options": options,
            "needs_image_options": needs_image_options,
            "likely_has_diagram": diagram_signal,
            "likely_has_formula": formula_signal,
        })
    return questions


_LEVEL_LABEL_RE = re.compile(r"level\s+\d+-\d+", re.IGNORECASE)
_SUBHEADER_WORD_RE = re.compile(r"\b(question|answer|points|marks|ans\.?|q)\b", re.IGNORECASE)


def _group_column_bounds(data_row, n_groups, group_index):
    """These tables vary a lot across years -- 'LEVEL' vs 'Level', a
    QUESTION/Q sub-column per level vs none, POINTS vs MARKS vs ANS. -- so
    trying to line up a boundary with *header* text (as the 2025-2026-only
    version of this function did) breaks the moment a year's header
    doesn't literally repeat a marker word once per level: the header
    label's x-position doesn't reliably line up with its own data columns
    (confirmed the hard way earlier -- see git history), so a boundary
    derived from it can bleed a character or two into the next group.

    What's actually reliable: every *data* row has the same number of
    space-separated tokens per level-group (either 2: answer, points: or
    3: question, answer, points), optionally with one shared row-number
    token before the first group (years where the question number isn't
    repeated per level). So figure out the token layout from an actual
    data row instead of the header, and use real token positions as the
    column boundaries -- that can't drift out of alignment with the data
    because it *is* the data.
    """
    tokens = [(m.start(), m.end()) for m in re.finditer(r"\S+", data_row)]
    total = len(tokens)
    leading = 1 if total % n_groups != 0 and (total - 1) % n_groups == 0 else 0
    per_group = (total - leading) // n_groups
    if per_group <= 0:
        return None
    start_tok = leading + group_index * per_group
    end_tok = start_tok + per_group
    if start_tok >= total:
        return None
    x0 = tokens[start_tok][0]
    x1 = tokens[end_tok][0] if end_tok < total else None
    return x0, x1


def parse_answer_key(pdf_path, level_label):
    raw = run_pdftotext(pdf_path)
    lines = raw.split("\n")

    header_i = next(i for i, l in enumerate(lines) if len(_LEVEL_LABEL_RE.findall(l)) >= 2)
    level_labels = _LEVEL_LABEL_RE.findall(lines[header_i])
    target = re.sub(r"\s+", " ", level_label).strip().lower()
    matches = [i for i, lbl in enumerate(level_labels) if re.sub(r"\s+", " ", lbl).strip().lower() == target]
    if not matches:
        raise ValueError(f"Level {level_label!r} not found among {level_labels}")
    group_index = matches[0]

    data_lines = [l for l in lines[header_i + 1:] if l.strip()]
    n_levels = len(level_labels)

    # Learn the row layout (a shared leading row-number token before the
    # groups, or not; 2 or 3 tokens per group) from the first data row,
    # which -- by these papers' own convention -- always has every level's
    # column populated (the lowest levels have the fewest questions, so if
    # any row has all of them, row one does). Reusing this rather than
    # inferring it fresh per row also survives a stray "VOID" cell (some
    # older years void out a bad question for one level) -- VOID is a
    # single token exactly like a letter grade would be, so it doesn't
    # change the token count, but *counting* valid answer letters (an
    # earlier version of this function did that) would have miscounted it
    # as a missing group and thrown off every group index on that row.
    first_row = next((l for l in data_lines if l.split(None, 1)[0][:1].isdigit()
                       and not _SUBHEADER_WORD_RE.search(l)), None)
    if first_row is None:
        return {}
    first_total = len(re.findall(r"\S+", first_row))
    leading = 1 if first_total % n_levels != 0 and (first_total - 1) % n_levels == 0 else 0
    if (first_total - leading) % n_levels != 0:
        return {}  # layout doesn't match any known pattern; give up rather than guess
    per_group = (first_total - leading) // n_levels

    # Column positions still drift by a character or two row to row in
    # these pdftotext-flattened tables (a double-digit question number
    # shifts everything after it, for instance), so bounds are still
    # recomputed from each row's own tokens, just using the group count
    # and layout learned above instead of re-deriving them per row.
    answers = {}
    qnum = 0
    for line in data_lines:
        first_token = line.split(None, 1)[0]
        if not first_token[:1].isdigit() and _SUBHEADER_WORD_RE.search(line):
            continue  # a repeated "QUESTION ANSWER POINTS"-style sub-header row
        # Every remaining line is a genuine question row -- count it even if
        # the rest of this iteration bails out below, so a row we can't
        # parse (e.g. one year has a one-off "A or B or D or E" answer for
        # a level that isn't even our target, which throws the token count
        # off for the whole row) costs only that one question's answer,
        # not a permanent off-by-one shift on every question after it.
        qnum += 1

        total = len(re.findall(r"\S+", line))
        if (total - leading) <= 0 or (total - leading) % per_group != 0:
            continue
        n_present = (total - leading) // per_group
        if n_present <= 0 or n_present > n_levels:
            continue
        # The lower levels have fewer questions (e.g. Level 1-2 and 3-4
        # often stop at 24 while 5-6 and up run to 30), so past a certain
        # row only a suffix of the level columns still has data -- shift
        # which group index we're after to match.
        row_group_index = group_index - (n_levels - n_present)
        if row_group_index < 0:
            continue  # this row has no data for our target level at all

        bounds = _group_column_bounds(line, n_present, row_group_index)
        if bounds is None:
            continue
        x0, x1 = bounds
        cell = line[x0:x1].strip()
        tokens = cell.split()
        if len(tokens) < 2:
            continue
        answer, points = tokens[-2], tokens[-1]
        if not points.isdigit() or not re.fullmatch(r"[A-EΑΒΓΔΕ]", answer):
            continue  # e.g. a voided question for this level -- leave it unanswered
        answers[qnum] = {"answer": GREEK_LETTER_TO_LATIN.get(answer, answer), "points": int(points)}
    return answers


def build(problems_pdf, answers_pdf, level_label, course_id, name, source, image_path):
    questions = parse_problems(problems_pdf)
    answers = parse_answer_key(answers_pdf, level_label)

    out_questions = []
    review = []
    for q in questions:
        ans = answers.get(q["number"])
        if ans is None:
            review.append(f"Q{q['number']}: no answer-key entry found for {level_label!r}")
        entry = {
            "number": q["number"],
            "text": q["text"],
            "options": q["options"],
            "answer": ans["answer"] if ans else None,
            "points": ans["points"] if ans else None,
        }
        if q["needs_image_options"] or q["likely_has_diagram"]:
            entry["image"] = f"q{q['number']}.png"  # placeholder -- crop and confirm manually
            review.append(
                f"Q{q['number']}: {'options are visual, ' if q['needs_image_options'] else ''}"
                f"{'diagram likely present, ' if q['likely_has_diagram'] else ''}"
                "crop images/{}/q{}.png manually".format(course_id, q['number'])
            )
        if q["likely_has_formula"]:
            review.append(
                f"Q{q['number']}: text may contain a mangled multi-line formula/fraction -- "
                "re-read against the PDF and rewrite the prompt text by hand"
            )
        out_questions.append(entry)

    course = {
        "id": course_id,
        "name": name,
        "source": source,
        "imagePath": image_path,
        "questions": out_questions,
    }
    return course, review


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("problems_pdf")
    ap.add_argument("answers_pdf")
    ap.add_argument("--level", required=True, help='e.g. "LEVEL 5-6"')
    ap.add_argument("--id", required=True, dest="course_id")
    ap.add_argument("--name", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--image-path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    course, review = build(
        args.problems_pdf, args.answers_pdf, args.level,
        args.course_id, args.name, args.source, args.image_path,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(course, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {args.out} ({len(course['questions'])} questions)", file=sys.stderr)
    if review:
        print("\nManual review needed:", file=sys.stderr)
        for line in review:
            print(" -", line, file=sys.stderr)


if __name__ == "__main__":
    main()
