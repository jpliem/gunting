# gunting-paper-audit

Multi-agent fraud + quality audit for research papers. Built to surface paper-mill /
fabrication signals (motivated by recent Indonesian paper-mill scandals).

You give it a PDF. It extracts the text, runs 9 web-enabled specialist auditors in parallel,
and a synthesizer produces a single annotated **fraud-risk report**.

## Use

In Claude Code, from this project:

```
/audit-paper path/to/paper.pdf
```

Output lands in `audit-work/<paper-slug>/REPORT.md`.

## What it checks (9 dimensions)

| Agent | Looks for |
|-------|-----------|
| methodology-auditor   | design soundness, reproducibility, methods support claims |
| results-auditor       | data integrity, stats validity, figure/table-vs-text consistency |
| author-auditor        | real affiliations, publication history, paper-mill signals, Retraction Watch |
| duration-auditor      | research timeline feasibility vs scope |
| findings-auditor      | conclusions supported by data, overclaiming |
| summary-auditor       | abstract matches body, no phantom results |
| formatting-auditor    | tortured phrases, template artifacts, citation/DOI anomalies |
| inconsistency-auditor | internal contradictions, number/sample-size drift |
| plausibility-auditor  | unrealistic / illogical claims, too-clean stats, impossible values |

A `audit-synthesizer` merges all findings → per-dimension risk scores, an overall verdict
(Clean / Minor / Serious / Likely fraud), severity-ranked flags, annotated suspect passages,
and cited web sources.

## Requirements

- PDF text extractor: **poppler** (`pdftotext`, `pdfinfo`) preferred, or `pip install pdfplumber`.
- Network access (specialists verify citations, authors, retractions via web).
- Scanned-image PDFs need OCR first (e.g. `ocrmypdf`) — extraction aborts with a clear message.

## Layout

```
.claude/agents/        9 specialist auditors + audit-synthesizer
.claude/skills/audit-paper/   orchestrator skill
scripts/extract.sh     PDF → page-marked text + meta.json
audit-work/            per-paper working dirs + REPORT.md (gitignored)
docs/superpowers/specs/  design spec (schema, scoring)
```

## Limits (v1)

Text + metadata reasoning only — no pixel-level image forensics. Single-paper flow (no batch UI).
Findings are decision support, not proof; CRITICAL/HIGH flags warrant human follow-up and author response.
