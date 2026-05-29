#!/usr/bin/env bash
# extract.sh <pdf-path> <out-dir>
# Extract PDF text (page-marked) + best-effort metadata for the audit pipeline.
set -euo pipefail

PDF="${1:-}"
OUT="${2:-}"

if [[ -z "$PDF" || -z "$OUT" ]]; then
  echo "usage: extract.sh <pdf-path> <out-dir>" >&2
  exit 2
fi
if [[ ! -f "$PDF" ]]; then
  echo "ERROR: PDF not found: $PDF" >&2
  exit 1
fi

mkdir -p "$OUT/findings"
TXT="$OUT/text.txt"
META="$OUT/meta.json"

extracted_with=""

# 1. Preferred: pdftotext -layout, then convert form-feeds into page markers.
if command -v pdftotext >/dev/null 2>&1; then
  raw="$(pdftotext -layout "$PDF" - 2>/dev/null || true)"
  if [[ -n "$raw" ]]; then
    # Split on form feed (\f) and prepend a page marker to each page.
    awk 'BEGIN{RS="\f"; p=0} {p++; printf("===== PAGE %d =====\n%s\n", p, $0)}' <<<"$raw" >"$TXT"
    extracted_with="pdftotext"
  fi
fi

# 2. Fallback: pdfplumber (python) if pdftotext missing or produced nothing.
if [[ -z "$extracted_with" ]]; then
  if command -v python3 >/dev/null 2>&1 && python3 -c "import pdfplumber" >/dev/null 2>&1; then
    python3 - "$PDF" "$TXT" <<'PY'
import sys, pdfplumber
pdf_path, out = sys.argv[1], sys.argv[2]
with pdfplumber.open(pdf_path) as pdf, open(out, "w") as f:
    for i, page in enumerate(pdf.pages, 1):
        f.write(f"===== PAGE {i} =====\n")
        f.write((page.extract_text() or "") + "\n")
PY
    extracted_with="pdfplumber"
  fi
fi

if [[ -z "$extracted_with" ]]; then
  echo "ERROR: no PDF extractor available. Install poppler (pdftotext) or 'pip install pdfplumber'." >&2
  exit 1
fi

# 3. Guard: scanned-image PDFs yield near-empty text.
chars="$(wc -c <"$TXT" | tr -d ' ')"
if [[ "$chars" -lt 500 ]]; then
  echo "ERROR: extracted text only ${chars} chars — PDF likely scanned images. OCR needed (e.g. ocrmypdf) before audit." >&2
  exit 1
fi

# 4. Best-effort metadata.
pages="$(awk '/^===== PAGE /{n++} END{print n+0}' "$TXT")"
title=""; author=""
if command -v pdfinfo >/dev/null 2>&1; then
  info="$(pdfinfo "$PDF" 2>/dev/null || true)"
  title="$(awk -F': *' '/^Title:/{ $1=""; sub(/^: */,""); print; exit}' <<<"$info" || true)"
  author="$(awk -F': *' '/^Author:/{ $1=""; sub(/^: */,""); print; exit}' <<<"$info" || true)"
fi
# DOI sniff from first ~2 pages.
doi="$(grep -oiE '10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+' "$TXT" | head -1 || true)"

# JSON-escape helper.
esc(){ printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

{
  printf '{\n'
  printf '  "source_pdf": %s,\n' "$(esc "$PDF")"
  printf '  "title": %s,\n'      "$(esc "$title")"
  printf '  "author": %s,\n'     "$(esc "$author")"
  printf '  "doi": %s,\n'        "$(esc "$doi")"
  printf '  "pages": %s,\n'      "${pages:-0}"
  printf '  "chars": %s,\n'      "${chars:-0}"
  printf '  "extracted_with": %s\n' "$(esc "$extracted_with")"
  printf '}\n'
} >"$META"

echo "OK: extracted ${chars} chars, ${pages} pages with ${extracted_with}"
echo "  text: $TXT"
echo "  meta: $META"
