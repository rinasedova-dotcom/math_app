`problems.pdf` in this folder is Greek-only (no "ENGLISH VERSION" section, unlike
most other years), so the automated parser (`tools/parse_kmo.py`) does not apply.

`data/kmo-2012-e-st-dimotikou.json` was built by manually reading this PDF page by
page and translating each question to English by hand, then cross-checking the
computed answer against the extracted answer key (`answers/kmo-2012-e-st-dimotikou/answers.pdf`,
column "Ε΄ Δημ.-ΣΤ΄ Δημ.").
