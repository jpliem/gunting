# ✂️ gunting

**Scissors for paper mills.** A multi-agent research-fraud audit that runs inside
[Claude Code](https://claude.com/claude-code).

`gunting` (Indonesian: *scissors*) takes one research-paper PDF, extracts the text,
fans out **9 web-enabled specialist auditors** in parallel, and a synthesizer returns a
single annotated **fraud-risk report** — verdict, per-dimension scores, severity-ranked
flags, quoted suspect passages, and cited web sources.

Built in response to a wave of paper-mill and fabrication scandals involving Indonesian
research, but the audit is venue- and country-agnostic.

---

## Use

In Claude Code, from this project:

```
/audit-paper path/to/paper.pdf
```

The report lands in `audit-work/<paper-slug>/REPORT.md`.

## What it checks — 9 dimensions

| Agent | Looks for |
|-------|-----------|
| `methodology-auditor`   | design soundness, reproducibility, methods-support-claims, missing IRB/ethics |
| `results-auditor`       | data integrity, stats validity, figure/table-vs-text consistency |
| `author-auditor`        | real affiliations, publication history, expertise mismatch, paper-mill signals, Retraction Watch |
| `duration-auditor`      | research-timeline feasibility, compressed peer-review turnaround |
| `findings-auditor`      | conclusions supported by data, overclaiming, overgeneralization |
| `summary-auditor`       | abstract matches body, phantom results, omitted limitations |
| `formatting-auditor`    | tortured phrases, template artifacts, citation/DOI anomalies |
| `inconsistency-auditor` | internal contradictions, number/sample-size drift |
| `plausibility-auditor`  | unrealistic / illogical claims, too-clean stats, impossible values |

`audit-synthesizer` merges all findings → per-dimension risk, an overall verdict
(**Clean / Minor concerns / Serious concerns / Likely fraud**), severity-ranked flags,
annotated suspect passages, and deduped sources. Full agent catalog and JSON schema:
[AGENTS.md](AGENTS.md).

## Proven on real papers

Two end-to-end runs (May 2026):

- **Retracted paper-mill paper** (Hindawi *Comput. Intell. Neurosci.*, DOI `10.1155/2022/8358794`,
  PMC9420581) → **Likely fraud, 90/100**. Independently reconstructed the actual retraction
  reasons: a "Biomedical Diagnosis" title grafted onto an all-electrical body, numberless
  placeholder citations (incl. blank `Method in reference ___` table columns), an impossible
  error-vs-accuracy table, GA parameters for an algorithm never described, and a 5-day
  revised-to-accepted review window.
- **Genuine IEEE conference paper** (ICISS 2022) → **Minor concerns, 36/100**. No fabrication;
  flagged real fixable defects (an abstract metric mislabeled MSE vs the body's MAE, only 1 of
  4 declared scenarios reported, three non-matching value pairs).

The fraud-vs-legit gap (90 vs 36) is the point: the system discriminates, it doesn't just
flag everything.

## Benchmark & evaluation

A reproducible benchmark lives in [`benchmark/`](benchmark/) — built on the **Retraction Watch**
database (6,362 fraud positives extracted) and **PMC open-access** full text, with a pure-Python
scorer (AUC, P/R/F1, calibration/ECE, bootstrap CIs) and a lexical **fingerprint baseline**.
Writeup: [`benchmark/paper/paper.md`](benchmark/paper/paper.md).

Pilot (14 papers — 6 paper-mill retractions vs 8 high-integrity-venue controls):

| Detector | AUC | F1 (≥serious) | F1 (≥likely-fraud) |
|---|---|---|---|
| gunting (decomposed + web) | **1.00** | 1.00 | 0.29 |
| gunting (decomposed, no web) | **1.00** | 1.00 | 0.80 |
| monolithic LLM + web | **1.00** | 1.00 | 0.80 |
| vanilla LLM (no rubric) | **1.00** | 0.91 | 0.67 |
| lexical fingerprint baseline | **0.44** | **0.00** | **0.00** |

Headlines: **reasoning auditing crushes surface fingerprinting** on fluent modern mills
(AUC 1.00 vs 0.44 — the lexical detector scores 0 on every fluent mill); the integrity
dimensions (plausibility/methodology/results/inconsistency) separate fraud from legit by ~60
points; and `gunting` catches **freshly LLM-generated** fabrications (95, 82 / 100) it has never
seen — including by web-verifying that cited journals don't exist — while clearing an honest
synthetic control (5/100). The honest caveat: AUC = 1.0 reflects an *easy* negative class and a
small pilot; the open problem is that **"non-retracted" is not a safe negative label** (paper §5.4).
The harness scales to the full corpus unchanged.

## Requirements

- PDF text extractor: **poppler** (`pdftotext`, `pdfinfo`) preferred, or `pip install pdfplumber`.
- Network access (specialists verify citations, authors, and retractions via web).
- Scanned-image PDFs need OCR first (e.g. `ocrmypdf`) — extraction aborts with a clear message.

## Layout

```
.claude/agents/               9 specialist auditors + audit-synthesizer
.claude/skills/audit-paper/   orchestrator skill
scripts/extract.sh            PDF → page-marked text + meta.json
docs/superpowers/specs/       design spec (schema, scoring)
audit-work/                   per-paper working dirs + REPORT.md (gitignored)
```

## Limits

Text + metadata reasoning on **one paper at a time**. It does **not**:

- do pixel-level image forensics on figures;
- correlate **across a set of submissions** — alias rings, duplicate datasets under different
  author names, or submitter-vs-author-list mismatch. That cross-document signature is the
  core of conference-scale identity-manipulation fraud (e.g. the 2026 ISPPD Copenhagen case)
  and is out of scope for a single-PDF audit.

Findings are decision support, not proof; CRITICAL/HIGH flags warrant human follow-up and
author response.

## Roadmap

- **`identity-cluster` mode** — ingest a *set* of submissions (one conference/author batch) and
  flag: shared writing/style fingerprints across different author names, duplicate
  figures/datasets, no-verifiable-footprint authors, multi-country/no-local-collaborator
  clusters, and submitter↔author-list mismatch. This is the piece that turns "audits a paper"
  into "catches a paper mill."
- Optional `scripts/fetch_pmc.sh <PMCID>` to pull open-access full text (DOI→PMCID→BioC),
  bypassing publisher PDF paywalls.

## License

[MIT](LICENSE).

> Not affiliated with any institution or publisher. An assistive screening tool — verdicts are
> hypotheses for human reviewers, never an accusation of misconduct on their own.
