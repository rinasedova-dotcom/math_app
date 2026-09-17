Both `problems.pdf` and `answers/kmo-2011-e-st-dimotikou/answers.pdf` in this course have
corrupted font encoding — `pdftotext` extracts a Greek-letter substitution cipher
(same class of issue as CMO 2015's answers PDF), so they could not be parsed
automatically.

`data/kmo-2011-e-st-dimotikou.json` was built by rendering each PDF page to an
image (the visual glyphs are unaffected by the text-layer corruption) and
manually reading and translating the Greek questions to English, then
cross-checking each computed answer against the answer key rendered the same way
(column "Ε΄ - ΣΤ΄ ΔΗΜ").

Note: for Q5, the official answer key lists two accepted answers (Δ and Ε) for
this grade column, likely due to an ambiguity/error acknowledged by the setters.
We recorded Δ (3), which is the answer directly supported by the literal wording
of the question.
