# Math Quiz

A static, no-backend website for practicing multiple-choice math competition
questions (Kangourou, Cyprus Mathematical Olympiad, etc.), Level 5-6 / 5th &
6th grade only. Shows a random question, lets the student pick an answer,
reveals right/wrong immediately, and keeps a full history of every answer
(with date/time) in the browser's local storage — no login, no server.

## Running it

This is a plain static site (HTML/CSS/JS, no build step), but it loads its
data with `fetch()`, so it must be served over HTTP — opening `index.html`
directly (`file://...`) will fail to load the course data due to browser
CORS restrictions.

```bash
cd math_app
python3 -m http.server 8000
# open http://localhost:8000/
```

Any static host works the same way (GitHub Pages, Netlify, S3, etc.) — just
publish the whole `math_app` folder.

## How it works

- **`index.html`** — pick which course(s) to practice, then start.
- **`quiz.html`** — shows one random question from the selected course(s),
  lets you pick an answer, highlights the correct option (green) and your
  choice if wrong (red), then lets you move to the next question.
- **`results.html`** — every answer ever given (question, your answer,
  correct answer, right/wrong, timestamp), filterable by course and
  outcome, with running accuracy stats. Stored in `localStorage`, so it is
  per-browser/per-device only, and `Clear all results` wipes it.

## Folder structure

```
problems/<course-id>/problems.pdf   original problem-set PDF (kept for reference)
answers/<course-id>/answers.pdf     original answer-key PDF (kept for reference)
data/courses.json                   manifest of available courses
data/<course-id>.json               extracted questions for that course (what the site actually reads)
images/<course-id>/*.png            cropped diagrams referenced by data/<course-id>.json
```

The site does **not** parse PDFs in the browser — these source PDFs mix
bilingual text, embedded diagrams and answer-key tables in ways that are not
reliable to parse automatically client-side. Instead each course is
pre-extracted once into a clean `data/<course-id>.json` file (question text,
answer options, correct answer, points, and any diagram image/table),
similar to how these two sample courses were built.

## Adding a new course

1. Drop the two source PDFs into `problems/<course-id>/problems.pdf` and
   `answers/<course-id>/answers.pdf`.
2. Extract the **Level 5-6** (or equivalent "5th & 6th grade") column from
   the answer-key PDF into a simple question-number → correct-letter
   mapping.
3. Extract each question's text and options from the problem PDF. Where a
   question has a genuine diagram (not just numeric options), crop it out
   of the PDF as a PNG into `images/<course-id>/qN.png` — `pdftoppm` /
   PyMuPDF (`fitz`) work well for this: render the page, then crop the
   figure's bounding box. Small structured grids (like a magic-square
   puzzle) can instead be written as a `"table"` array (see the example
   below) rather than an image, which renders sharper.
4. Write `data/<course-id>.json` with this shape:

```json
{
  "id": "course-id",
  "name": "Display name shown in the course picker",
  "source": "Where this paper is from",
  "imagePath": "images/course-id",
  "questions": [
    {
      "number": 1,
      "text": "Question text.",
      "image": "q1.png",            // optional
      "table": [["1","2"],["3","4"]], // optional, alternative to image
      "options": [
        {"label": "A", "text": "..."},
        {"label": "B", "text": "..."}
      ],
      "answer": "B",
      "points": 3
    }
  ]
}
```

   If a question's options are themselves purely visual (e.g. "which
   pattern completes the picture"), leave `"text": ""` on each option — the
   image already shows the labeled choices, and the app just renders plain
   lettered buttons for picking one.

5. Add an entry to `data/courses.json` pointing at the new file. The course
   picker on the home page and the quiz pool pick it up automatically.
