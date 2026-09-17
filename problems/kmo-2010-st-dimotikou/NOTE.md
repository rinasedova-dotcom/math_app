Unlike the other years in this project, the 2010 Olympiad used separate, differently-worded
problem booklets per grade (Δ' Δημοτικού / Ε' Δημοτικού / ΣΤ' Δημοτικού each had their own
30 questions), rather than a single combined "Ε'-ΣΤ' Δημοτικού" booklet. The only problems
PDF available for 2010 is the **ΣΤ' Δημοτικού (6th grade)** booklet, so this course is scoped
to 6th grade only — there is no matching 5th-grade paper to combine it with.

`problems.pdf` is Greek-only (no "ENGLISH VERSION" section) with a clean, readable text
layer, so `data/kmo-2010-st-dimotikou.json` was built by reading it directly and translating
each of the 30 questions to English by hand. Answers were taken from the "ΣΤ' ΔΗΜΟΤΙΚΟΥ"
column of `answers/kmo-2010-st-dimotikou/answers.pdf` (which also lists separate Δ' and Ε'
columns for the other grades' booklets, not used here) and cross-checked computationally
against each question.

No points-per-question legend was found in the source PDF (unlike other years), so all
30 questions are scored at a flat 4 points.
