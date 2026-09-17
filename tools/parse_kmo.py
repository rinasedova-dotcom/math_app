"""Parser for the Cyprus Mathematical Society / Cyprus Math Olympiad style
PDFs: a single problems PDF containing a full Greek edition followed by a
full "ENGLISH VERSION" edition (one exam paper = one grade already, so no
level/column choice needed there), and a separate multi-grade answers PDF
where each grade is one column in a table (no per-question points column --
these papers use a flat points-per-correct-answer scheme stated in the
instructions, not shown per question).

Usage:
    python3 parse_kmo.py problems.pdf answers.pdf --grade "5th & 6th grade" \
        --out data/course-id.json --id course-id --name "Display name" \
        --source "..." --image-path images/course-id --points 4
"""
import argparse
import json
import re
import sys

from pdf_common import (
    run_pdftotext, is_greek_line, strip_greek_asides, collapse_ws,
    max_blank_run, GREEK_LETTER_TO_LATIN, fix_stray_greek_letters,
    likely_has_stacked_formula, _detect_repeated_header, _header_key,
)

QUESTION_START_RE = re.compile(r"^\s{0,6}(\d{1,2})\.\s*(.*)$")
OPTION_LABELS = "".join(GREEK_LETTER_TO_LATIN)  # "ΑΒΓΔΕ"
OPTION_LINE_RE = re.compile(rf"^\s*[{OPTION_LABELS}]\.\s")
OPTION_SPLIT_RE = re.compile(rf"\s{{2,}}(?=[{OPTION_LABELS}]\.\s)")
OPTION_TOKEN_RE = re.compile(rf"^([{OPTION_LABELS}])\.\s*(.*)$")

EXCLUDE_PAGE_MARKERS = ("EXAM PAPER", "TIME:", "Examples of filling")


def _english_content_pages(raw_text):
    pages = raw_text.split("\x0c")
    start = next(i for i, p in enumerate(pages) if "ENGLISH VERSION" in p)
    kept_raw = [p for p in pages[start + 1:] if p.strip() and not any(m in p for m in EXCLUDE_PAGE_MARKERS)]
    # Not every year's "English" pages actually translate the running
    # header/footer too -- some (e.g. 2013) keep a one-line Greek header
    # and a Greek "Σελίδα N" footer even though the question text itself
    # is in English. Detecting the repeated header instead of assuming a
    # fixed 2-line count (see pdf_common._detect_repeated_header) avoids
    # eating a real question line when that year only has one header line.
    header_sig = _detect_repeated_header(kept_raw)
    content = []
    for page in kept_raw:
        lines = page.split("\n")
        if header_sig and tuple(_header_key(l) for l in lines[:len(header_sig)]) == header_sig:
            lines = lines[len(header_sig):]
        while lines and (not lines[-1].strip() or "Cyprus Mathematical Society" in lines[-1]
                          or re.match(r"^\s*Σελίδα\b", lines[-1])):
            lines.pop()
        content.append(lines)
    return content


def parse_problems(pdf_path):
    raw = run_pdftotext(pdf_path)
    pages = _english_content_pages(raw)

    all_lines = []
    for page in pages:
        all_lines.extend(page)
        all_lines.append("")

    raw_starts = []
    for i, line in enumerate(all_lines):
        m = QUESTION_START_RE.match(line)
        if m:
            raw_starts.append((i, int(m.group(1)), m.group(2)))

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
        # Option lines start with a Greek letter ("Α.", "Β.", ...) by
        # design in this paper, so the Greek-content filter below would
        # otherwise discard them outright -- keep any option-marker line
        # unconditionally, and only Greek-filter everything else.
        kept = [l for l in block if l.strip() and (OPTION_LINE_RE.match(l) or not is_greek_line(l))]

        option_line_idxs = [i for i, l in enumerate(kept) if OPTION_LINE_RE.match(l)]
        prompt_lines = kept[: option_line_idxs[0]] if option_line_idxs else kept
        prompt = fix_stray_greek_letters(collapse_ws(" ".join(prompt_lines)))

        options = []
        for oline in kept[option_line_idxs[0]:] if option_line_idxs else []:
            for seg in OPTION_SPLIT_RE.split(oline.strip()):
                m = OPTION_TOKEN_RE.match(seg)
                if m:
                    label = GREEK_LETTER_TO_LATIN[m.group(1)]
                    options.append({"label": label, "text": strip_greek_asides(m.group(2))})

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


def parse_answer_key(pdf_path, grade_label, grade_pattern=None):
    """Multi-line wrapped column headers (see pdf_common.find_column_range
    for why a simple single-line offset doesn't work here), one Greek
    answer letter per data cell, no points column.

    Most years' answer keys label columns in Greek even when the problems
    PDF has an English edition ("Ε΄ & ΣΤ΄ ΔΗΜΟΤΙΚΟΥ", "Ε΄-ΣΤ΄ ΔΗΜΟΤΙΚΟΥ",
    "Ε-ΣΤ" ...) -- the punctuation between the two grade codes varies by
    year, so plain-text matching on `grade_label` doesn't cover all of
    them. Pass `grade_pattern` (a raw regex, not escaped) to match those
    directly instead.
    """
    from pdf_common import find_column_range

    raw = run_pdftotext(pdf_path)
    lines = raw.split("\n")

    data_start = next(i for i, l in enumerate(lines) if re.match(r"^\s*\d+\s+\S", l))
    header_lines = lines[:data_start]
    data_lines = lines[data_start:]

    pattern = grade_pattern if grade_pattern else re.escape(grade_label).replace(r"\ ", r"\s*")
    x0, x1 = find_column_range(header_lines, pattern)

    answers = {}
    for line in data_lines:
        m = re.match(r"^\s*(\d+)\s", line)
        if not m:
            continue
        qnum = int(m.group(1))
        cell = line[x0:x1].strip()
        if not cell:
            continue
        letter = cell.split()[0]
        # A voided question (excluded from scoring for this grade) shows
        # up as "VOID"/"void" or a bare dash instead of a letter -- leave
        # it unanswered rather than storing punctuation as an "answer".
        if letter not in GREEK_LETTER_TO_LATIN and letter not in "ABCDE":
            continue
        answers[qnum] = GREEK_LETTER_TO_LATIN.get(letter, letter)
    return answers


def build(problems_pdf, answers_pdf, grade_label, course_id, name, source, image_path, points, grade_pattern=None):
    questions = parse_problems(problems_pdf)
    answers = parse_answer_key(answers_pdf, grade_label, grade_pattern=grade_pattern)

    out_questions = []
    review = []
    for q in questions:
        ans = answers.get(q["number"])
        if ans is None:
            review.append(f"Q{q['number']}: no answer-key entry found for {grade_label!r}")
        entry = {
            "number": q["number"],
            "text": q["text"],
            "options": q["options"],
            "answer": ans,
            "points": points,
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
    ap.add_argument("--grade", required=True, help='e.g. "5th & 6th grade"')
    ap.add_argument("--grade-regex", default=None,
                     help="raw regex to match the answer-key column when it's labeled in "
                          "Greek (e.g. r'\\u0395.{0,3}[-&].{0,3}\\u03a3\\u03a4') -- overrides --grade for that match only")
    ap.add_argument("--id", required=True, dest="course_id")
    ap.add_argument("--name", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--image-path", required=True)
    ap.add_argument("--points", type=int, default=4, help="flat points per correct answer")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    course, review = build(
        args.problems_pdf, args.answers_pdf, args.grade,
        args.course_id, args.name, args.source, args.image_path, args.points,
        grade_pattern=args.grade_regex,
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
