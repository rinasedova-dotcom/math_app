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
)

QUESTION_START_RE = re.compile(r"^\s{0,4}(\d{1,2})\.\s+(.*)$")
OPTION_TOKEN_RE = re.compile(r"\(([A-E])\)\s*([^()]*?)(?=\s*\([A-E]\)|$)")


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
        cleaned = [strip_greek_asides(l) if "(A)" in l or l.strip().startswith("(") else l for l in block]
        kept = [l for l in cleaned if l.strip() and not is_greek_line(l)]

        option_line_idxs = [i for i, l in enumerate(kept) if l.strip().startswith("(A)")]
        prompt_lines = kept[: option_line_idxs[0]] if option_line_idxs else kept
        prompt = fix_stray_greek_letters(collapse_ws(" ".join(prompt_lines)))

        options = []
        if option_line_idxs:
            option_lines = kept[option_line_idxs[0]:]
            for oline in option_lines:
                found = OPTION_TOKEN_RE.findall(oline)
                if len(found) > 1:
                    for label, text in found:
                        options.append({"label": label, "text": strip_greek_asides(text)})
                elif len(found) == 1:
                    label, text = found[0]
                    # a lone "(X) ..." line -- text may run to end of line
                    text = re.sub(r"^\([A-E]\)\s*", "", oline.strip())
                    options.append({"label": label, "text": strip_greek_asides(text)})
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


def parse_answer_key(pdf_path, level_label):
    """The header has two rows: 'LEVEL x-y' labels loosely centered over
    each 3-column group, then 'QUESTION ANSWER POINTS' repeated once per
    group. The LEVEL label's own x-position doesn't line up tightly with
    its data columns, but the two header rows list the same groups in the
    same left-to-right order -- so match by position-in-sequence (the Nth
    LEVEL label's data lives under the Nth QUESTION/ANSWER/POINTS triplet),
    not by character offset.
    """
    raw = run_pdftotext(pdf_path)
    lines = raw.split("\n")

    level_row = next(line for line in lines if line.count("LEVEL") >= 2)
    sub_row = next(line for line in lines if line.count("QUESTION") >= 2)
    data_lines = lines[lines.index(sub_row) + 1:]

    level_labels = [m.group() for m in re.finditer(r"LEVEL\s+\d+-\d+", level_row)]
    pattern = re.compile(re.escape(level_label).replace(r"\ ", r"\s*"), re.IGNORECASE)
    matches = [i for i, lbl in enumerate(level_labels) if pattern.fullmatch(lbl) or pattern.search(lbl)]
    if not matches:
        raise ValueError(f"Level {level_label!r} not found among {level_labels}")
    group_index = matches[0]

    question_starts = [m.start() for m in re.finditer(r"QUESTION", sub_row)]
    if group_index >= len(question_starts):
        raise ValueError("Level/QUESTION column count mismatch in answer key header")
    x0 = question_starts[group_index]
    x1 = question_starts[group_index + 1] if group_index + 1 < len(question_starts) else None

    answers = {}
    for line in data_lines:
        if not line.strip():
            continue
        cell = line[x0:x1].strip()
        if not cell:
            continue
        parts = cell.split()
        if len(parts) != 3 or not parts[0].isdigit() or not parts[2].isdigit():
            continue
        qnum, answer, points = parts
        answers[int(qnum)] = {"answer": answer, "points": int(points)}
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
