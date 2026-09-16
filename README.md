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
2. If the PDFs match one of the two layouts already seen (THALES/Kangourou,
   or Cyprus Mathematical Society/KMO), run the matching script in
   `tools/` — `parse_kangourou.py` or `parse_kmo.py` — to generate most of
   `data/<course-id>.json` automatically (question text, options and the
   correct-answer column are extracted by regex over `pdftotext -layout`
   output). See `tools/README.md` for usage and what still needs a manual
   pass afterward (mainly: cropping diagrams — the scripts can't see
   images, only flag which questions likely need one). For a genuinely new
   layout, there's no shortcut yet; extract by hand the same way, using the
   steps below as a guide, and consider writing a third script once the
   layout is understood.
3. Whichever way you built it, `data/<course-id>.json` should end up with
   this shape:

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

4. Add an entry to `data/courses.json` pointing at the new file. The course
   picker on the home page and the quiz pool pick it up automatically.
