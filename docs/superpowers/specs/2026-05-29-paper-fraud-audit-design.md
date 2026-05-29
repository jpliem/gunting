# Paper Fraud Audit — Design Spec

Date: 2026-05-29
Project: `gunting-paper-audit`

## Purpose

Audit research papers (PDF) for fraud and quality signals, motivated by paper-mill /
fabrication patterns. Produce an annotated report with a fraud-risk verdict, severity-ranked
flags, evidence, web-verified sources, and inline-quoted suspect passages.

## Run model

Claude Code project-local subagents in `.claude/agents/`, orchestrated by the `audit-paper`
skill. All specialist agents are **web-enabled** (WebSearch/WebFetch) for external verification.

## Pipeline

```
PDF → [extract] → text + page map → orchestrator
                                        ├─ fan out 9 specialists (parallel)
                                        └─ synthesizer → REPORT.md (+ suspect-quote appendix)
```

Working dir per run: `audit-work/<paper-slug>/`
- `text.txt`        — extracted text, page markers preserved
- `meta.json`       — title, authors, doi (if found), page count, extraction tool
- `findings/<agent>.json` — each specialist's structured output
- `REPORT.md`       — synthesizer output

## Extraction

`scripts/extract.sh <pdf> <out-dir>`:
1. `pdftotext -layout` → `text.txt`. Insert `\f`-derived `===== PAGE N =====` markers.
2. Fallback `pdfplumber` (python) if `pdftotext` missing.
3. Write `meta.json` (best-effort title/author/doi from first page + `pdfinfo`).
4. Abort with clear error if PDF unreadable or text < 500 chars (likely scanned image → note OCR needed).

## Specialist agents (9)

Each: web-enabled, single dimension, returns **one fenced ```json block** matching Finding Schema,
preceded by 2-3 sentence prose summary.

| Agent | Dimension key | Audits |
|-------|---------------|--------|
| `methodology-auditor`   | `methodology`   | design soundness, reproducibility, methods support the claims, sample/controls adequate |
| `results-auditor`       | `results`       | data integrity, stat validity, figures/tables consistent with text, error bars / p-values sane |
| `author-auditor`        | `author`        | affiliations exist, publication history, paper-mill / authorship-for-sale signals, Retraction Watch hits |
| `duration-auditor`      | `duration`      | stated research timeline feasible vs scope (data collection, follow-up, cohort windows) |
| `findings-auditor`      | `findings`      | conclusions supported by presented data, overclaiming, causal leaps |
| `summary-auditor`       | `summary`       | abstract/conclusion match body, no phantom results, no claims absent from body |
| `formatting-auditor`    | `formatting`    | template artifacts, tortured phrases, citation-format anomalies, paper-mill fingerprints, broken refs |
| `inconsistency-auditor` | `inconsistency` | internal contradictions across sections, number/unit mismatches, sample-size drift |
| `plausibility-auditor`  | `plausibility`  | unrealistic/illogical claims, too-clean stats, physically impossible values, timeline-vs-duration mismatch |

## Finding Schema (every specialist returns this)

```json
{
  "dimension": "methodology",
  "agent": "methodology-auditor",
  "summary": "one-line dimension verdict",
  "dimension_risk": 0,
  "flags": [
    {
      "id": "methodology-1",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "claim": "what the paper states",
      "issue": "what is wrong / suspicious",
      "evidence": "reasoning or web finding",
      "location": "section / page N / quoted snippet",
      "sources": ["url1", "url2"],
      "confidence": "high|medium|low"
    }
  ]
}
```

- `dimension_risk`: 0-100 (0 clean, 100 certain fraud).
- No flags → empty `flags: []`, `dimension_risk: 0`.
- Web lookup fails → still emit flag with `confidence: low` and note "unverified — network", never crash.
- Always cite a `location` so synthesizer can build the annotated appendix.

## Severity → risk guidance

- CRITICAL: direct fabrication/falsification evidence, impossible data, confirmed retraction/mill → pushes dimension_risk ≥ 80.
- HIGH: strong unexplained anomaly → 60-79.
- MEDIUM: quality/integrity concern needing explanation → 30-59.
- LOW: minor / stylistic → 1-29.

## Synthesizer

`audit-synthesizer` agent. Input: all `findings/*.json`. Output `REPORT.md`:

1. **Verdict header** — overall risk score + label, one-paragraph rationale.
   - Overall = max(dimension_risk) if any CRITICAL flag exists, else weighted mean (integrity dims
     methodology/results/inconsistency/plausibility weighted 1.5×, others 1×).
   - Labels: 0-19 Clean · 20-39 Minor concerns · 40-69 Serious concerns · 70-100 Likely fraud.
2. **Risk table** — per-dimension score + label.
3. **Flags, severity-ranked** — CRITICAL→LOW, each with claim/issue/evidence/location/sources.
4. **Annotated suspect passages** — inline-quoted snippets (from `location`) grouped by section.
5. **Sources** — deduped list of all web URLs cited.
6. **Limitations** — extraction gaps, unverified items, scanned-image notes.

Dedupe flags that reference same location+issue across agents; keep highest severity, merge sources.

## Orchestrator skill `audit-paper`

`/audit-paper <pdf-path>`:
1. Run `scripts/extract.sh`. Abort on failure.
2. Read `text.txt` length; warn if OCR likely.
3. Dispatch 9 specialists in parallel (single message, multiple Agent calls), each given path to
   `text.txt` + `meta.json` and instructed to write `findings/<agent>.json`.
4. After all return, dispatch `audit-synthesizer`.
5. Print verdict header + path to `REPORT.md`.

## Error handling

- Extraction fail → abort, tell user (try OCR / re-export PDF).
- A specialist errors → synthesizer notes dimension as "not audited" in Limitations, continues.
- Network down → specialists degrade to internal-only with `confidence: low`.

## Out of scope (YAGNI)

- Image forensics on figures (pixel-level) — text/metadata reasoning only for v1.
- Batch/dashboard UI — single-paper CLI flow only.
- Plagiarism corpus matching beyond web search.
