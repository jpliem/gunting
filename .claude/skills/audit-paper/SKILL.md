---
name: audit-paper
description: Audit a research paper PDF for fraud and quality signals (paper-mill / fabrication detection). Runs extraction, 9 parallel specialist auditors, and a synthesizer to produce an annotated fraud-risk report. Trigger when the user wants to audit/vet/fact-check a paper or check it for fraud.
---

# audit-paper

Orchestrates the full paper fraud audit. Input: a PDF path (the user gives `/audit-paper <pdf>`).

## Steps — follow in order

### 1. Extract
Pick a slug from the PDF filename (lowercase, kebab). Working dir = `audit-work/<slug>/`.
Run:
```
bash scripts/extract.sh "<pdf-path>" "audit-work/<slug>"
```
If it exits non-zero, STOP and relay the error to the user (e.g. scanned PDF needs OCR). Do not continue.

### 2. Sanity check
Read `audit-work/<slug>/meta.json`. If `chars` is low or pages look truncated, warn the user but proceed.

### 3. Fan out 9 specialists IN PARALLEL
In a SINGLE message, dispatch all 9 via the Agent tool (one tool call each, same block so they run concurrently). Give every agent this same context, substituting the real workdir:

> Audit the paper for your dimension. Text: `audit-work/<slug>/text.txt` (has `===== PAGE N =====` markers). Metadata: `audit-work/<slug>/meta.json`. Write your findings JSON to `audit-work/<slug>/findings/<your-key>.json` per your instructions, then summarize.

Agents and their subagent_type:
- methodology-auditor
- results-auditor
- author-auditor
- duration-auditor
- findings-auditor
- summary-auditor
- formatting-auditor
- inconsistency-auditor
- plausibility-auditor

Wait for all to return. If one fails, note it and continue — the synthesizer marks missing dimensions.

### 4. Synthesize
Dispatch `audit-synthesizer` with: workdir `audit-work/<slug>/`. It reads `findings/*.json` + `meta.json` and writes `audit-work/<slug>/REPORT.md`.

### 5. Report back
Print the verdict header (label + overall score) and the path to `REPORT.md`. Offer to open / summarize the top CRITICAL/HIGH flags.

## Notes
- All specialists are web-enabled; the audit needs network for citation/author/Retraction-Watch checks. If offline, results degrade (flags marked low-confidence) but still run.
- v1 does text + metadata reasoning only — no pixel-level image forensics.
- Schema + scoring detail: `docs/superpowers/specs/2026-05-29-paper-fraud-audit-design.md`.
