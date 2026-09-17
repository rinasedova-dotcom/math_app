`problems.pdf` has corrupted font encoding — `pdftotext` extracts a Greek-letter
substitution cipher (same class of issue as CMO 2011/2015), so it could not be
parsed automatically. However, the answers PDF's text layer is *not* corrupted
and extracts cleanly.

`data/kmo-2020-e-st-dimotikou.json` was built primarily from screenshots of the
questions the user supplied directly in chat, cross-checked against this
problems PDF (rendered to page images, since the visual glyphs are unaffected
by the text-layer corruption) for exact figures. Answers were taken from the
"Ε΄ & ΣΤ΄ Δημοτικού" column of `answers/kmo-2020-e-st-dimotikou/answers.pdf`
and cross-checked computationally — 20 of the 25 answers were independently
re-derived by solving each question and matched the extracted key exactly.
