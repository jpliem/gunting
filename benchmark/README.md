# gunting benchmark — paper-mill detection evaluation harness

A fully reproducible benchmark for LLM-based research-fraud detection, built on the
**Retraction Watch** database (reliable fraud positives) and **PMC open-access**
full text. Pure-Python (no pandas/sklearn/numpy); LLM configs run via the project's
audit agents.

**Read the writeup:** [`paper/paper.md`](paper/paper.md).

## TL;DR results (14-paper pilot: 6 paper-mill positives / 8 high-integrity-venue controls)

| Config | AUC | F1 @≥serious | F1 @≥likely-fraud | ECE |
|---|---|---|---|---|
| gunting (decomposed + web) | **1.00** | 1.00 | 0.29 | 0.19 |
| gunting (decomposed, no web) | **1.00** | 1.00 | 0.80 | 0.17 |
| monolithic + web | **1.00** | 1.00 | 0.80 | 0.15 |
| vanilla LLM (no rubric, no web) | **1.00** | 0.91 | 0.67 | 0.19 |
| **lexical fingerprint baseline** | **0.44** | **0.00** | **0.00** | 0.45 |

Adversarial (freshly LLM-generated, blind): fabricated ML **95**, fabricated biomed
**82**, honest control **5**.

**Caveat:** AUC = 1.0 reflects an *easy* negative class (reputable venues) and a tiny
pilot. The real difficulty is the negative class — see §5.4 of the paper.

## Layout

```
benchmark/
├── paper/paper.md              # the writeup (results + limitations)
├── harness/
│   ├── build_dataset.py        # Retraction Watch CSV -> fraud-positive candidates
│   ├── fetch_text.py           # PMID/PMCID/DOI -> PMC BioC full text (gunting layout)
│   └── sanitize.py             # strip retraction-notice leakage; drop unsanitizable
├── baselines/fingerprint/
│   └── fingerprint_detect.py   # tortured-phrase + structural lexical detector
├── scoring/
│   ├── score.py                # AUC, P/R/F1, specificity, ECE, bootstrap CIs
│   ├── results.json            # machine-readable metrics
│   └── per_paper_scores.csv    # every paper × every config
├── sets/
│   ├── candidates.jsonl        # 6,362 RW fraud positives
│   ├── labeled.jsonl           # the 14-paper pilot (id,label,note,text path)
├── runs/
│   ├── gunting_web.jsonl  gunting_noweb.jsonl  mono_web.jsonl
│   ├── vanilla.jsonl  fingerprint.jsonl  adversarial.jsonl
│   ├── _hardneg_probe.jsonl    # same-domain non-retracted "controls" (§5.4)
│   └── _text/<PMCID>/text_clean.txt   # sanitized full texts
└── data/retraction_watch.csv   # CC0 snapshot (regenerate: see below)
```

## Reproduce

### 0. Data (network)
```bash
# Retraction Watch (CC0, via Crossref Labs)
curl -L "https://api.labs.crossref.org/data/retractionwatch?mailto=YOU@example.com" \
  -o data/retraction_watch.csv
```

### 1. Build the positive pool
```bash
python3 harness/build_dataset.py --rw data/retraction_watch.csv --out sets/candidates.jsonl
```

### 2. Fetch full text (positives + controls), then sanitize leakage
```bash
# fetch_text.py resolves PMID/PMCID/DOI -> PMC BioC full text
python3 harness/fetch_text.py --pmcid PMC7840786 --label 1 --out runs/_text/PMC7840786
python3 harness/sanitize.py --labels sets/labeled.jsonl   # strips retraction notices
```

### 3. Run detectors
- **Fingerprint baseline (instant):**
  ```bash
  python3 baselines/fingerprint/fingerprint_detect.py --labels sets/labeled.jsonl --out runs/fingerprint.jsonl
  ```
- **LLM configs:** run the project's `audit-paper` agents over each `runs/_text/<id>/text_clean.txt`
  under each condition (decomposed/monolithic × web/no-web), writing
  `{"id","score"}` rows to `runs/<config>.jsonl`. Anti-leakage rule: agents must NOT
  look up the paper's own retraction status. (Prompts are documented in the paper, §4.)

### 4. Score
```bash
python3 scoring/score.py --labels sets/labeled.jsonl \
  --run gunting_web=runs/gunting_web.jsonl \
  --run gunting_noweb=runs/gunting_noweb.jsonl \
  --run mono_web=runs/mono_web.jsonl \
  --run vanilla=runs/vanilla.jsonl \
  --run fingerprint=runs/fingerprint.jsonl \
  --thresholds 40,70 --out scoring/results.json
```

## Scaling to the full corpus
`sets/candidates.jsonl` holds 6,362 fraud positives. To run at Pub-Guard scale
(~11k, mixed prevalence), select positives + a **label-safe** negative set (the open
problem — see paper §5.4), fetch text, and run steps 3–4. The harness is unchanged.

## Labels & ethics
Positives are public retractions (Retraction Watch, CC0). Controls are open-access
articles from high-integrity venues; inclusion is by venue, **not** by detector
score, to avoid selection bias. Texts are sanitized of retraction-status strings so
detectors cannot trivially win. Scores are research signals, **not** accusations.
