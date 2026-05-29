# Agents

`gunting` ships 10 Claude Code subagents (9 specialists + 1 synthesizer) plus an
orchestrator skill. All specialists are **web-enabled** and emit one machine-readable
JSON findings block per run.

## Orchestration

```
PDF ──> scripts/extract.sh ──> text.txt + meta.json
                                   │
                    audit-paper skill (orchestrator)
                                   │
        ┌──────────────────────────┴──────────────────────────┐
        │   9 specialists, dispatched in parallel (web-enabled) │
        └──────────────────────────┬──────────────────────────┘
                                   │ findings/<dim>.json
                          audit-synthesizer
                                   │
                            REPORT.md (verdict + annotated flags)
```

## Specialists

| Agent | Dimension | What it hunts |
|-------|-----------|---------------|
| `methodology-auditor`   | methodology   | design soundness, reproducibility, methods-support-claims, missing IRB/ethics, unnamed equipment |
| `results-auditor`       | results       | data integrity, stats validity, figure/table-vs-text consistency, impossible/too-clean numbers |
| `author-auditor`        | author        | affiliation reality, publication history, expertise mismatch, paper-mill signals, Retraction Watch |
| `duration-auditor`      | duration      | research-timeline feasibility vs scope, compressed peer-review turnaround |
| `findings-auditor`      | findings      | conclusions supported by data, overclaiming, causal leaps, overgeneralization |
| `summary-auditor`       | summary       | abstract matches body, phantom results, spin, omitted limitations |
| `formatting-auditor`    | formatting    | tortured phrases, template artifacts, citation/DOI anomalies, paper-mill fingerprints |
| `inconsistency-auditor` | inconsistency | internal contradictions, number/sample-size drift, citation-list mismatches |
| `plausibility-auditor`  | plausibility  | unrealistic/illogical claims, physically impossible values, timeline-vs-duration mismatch |

## Synthesizer

`audit-synthesizer` — merges all `findings/*.json`, dedupes flags that share a
location+issue, scores each dimension, computes the overall verdict, and writes
`REPORT.md` (verdict header, per-dimension risk table, severity-ranked flags,
annotated suspect passages, deduped sources, limitations).

## Finding schema

Every specialist returns:

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
      "sources": ["url"],
      "confidence": "high|medium|low"
    }
  ]
}
```

`dimension_risk` is 0–100. Severity→risk guidance: CRITICAL ≥80, HIGH 60–79,
MEDIUM 30–59, LOW 1–29. Network failure degrades a flag to `confidence: low`
("unverified — network") rather than crashing.

## Scoring

- Any CRITICAL flag anywhere → overall = `max(dimension_risk)`.
- Otherwise → weighted mean; integrity dimensions (methodology, results,
  inconsistency, plausibility) weighted ×1.5, the rest ×1.0.
- Labels: **0–19 Clean · 20–39 Minor concerns · 40–69 Serious concerns · 70–100 Likely fraud**.

## Scope & limits

`gunting` audits **one paper's text + metadata** per run. It does **not**:

- do pixel-level image forensics on figures;
- correlate **across** a set of submissions (alias rings, duplicate datasets under
  different author names, submitter-vs-author-list mismatch) — the signature of
  conference-scale paper-mill / identity-manipulation fraud. See the roadmap in
  [README](README.md) for the planned `identity-cluster` mode.
