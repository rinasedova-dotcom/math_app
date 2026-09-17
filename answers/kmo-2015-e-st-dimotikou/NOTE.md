`answers.pdf` in this folder has corrupted font encoding — `pdftotext` extracts
garbled characters (a consistent Greek-letter substitution cipher), so it
could not be parsed automatically or safely OCR'd with confidence.

The actual answer key used to build `data/kmo-2015-e-st-dimotikou.json` came
from a clean screenshot of the same table the user provided directly in
chat, not from this PDF.
