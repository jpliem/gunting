# Reasoning Auditors Beat Fingerprints but Inherit the Negative-Class Problem: A Pilot Benchmark for LLM Paper-Mill Detection

**Working paper / pilot study — v0.1, June 2026**

*Artifact: `gunting`, a 9-dimension multi-agent paper-fraud auditor, with a fully reproducible benchmark harness built on the Retraction Watch database and PubMed Central open-access full text.*

---

## Abstract

Paper mills and, increasingly, large language model (LLM) text generators produce
fluent fraudulent research at a scale that overwhelms peer review. Deployed
detectors largely rely on **surface fingerprints** (tortured phrases, template
artifacts, metadata anomalies) or single-model classifiers. We ask whether a
**decomposed, web-grounded reasoning auditor** improves detection and, critically,
whether it can be *evaluated honestly*. We build a reproducible benchmark from the
Retraction Watch database (reliable fraud **positives**) and PMC open-access full
text, and run a four-cell ablation — decomposition × web access — plus a lexical
fingerprint baseline, on a 14-paper balanced pilot (6 paper-mill retractions, 8
high-integrity-venue controls). Three findings stand out. (1) **Every reasoning
configuration separates fluent mills from reputable-venue papers perfectly
(AUC = 1.00), while the fingerprint baseline is worse than chance (AUC = 0.44,
recall = 0).** (2) The configurations differ not in discrimination but in
**calibration**: decomposed + weighted-mean aggregation is markedly more
conservative at the strict "likely-fraud" threshold (recall 0.17 vs 0.67), and web
grounding does not raise AUC on clean controls but enables catching **fabricated
citations** in novel fraud. (3) The hardest and most important problem is the
**negative class**: on same-domain *non-retracted* papers, even a no-rubric model
flags 5/7 as suspicious — these are either false positives or *undetected mills*,
and "non-retracted" is not a safe negative. We additionally show, against freshly
**LLM-generated** fabricated papers (the "BadScientist" threat), that the auditor
scores fabrications 82–95/100 while clearing an honest synthetic control at 5/100.
An **independent, offline, blinded replication** with a non-Claude model (Qwen3.6-35B)
reproduces the separation (holistic AUC 0.98) while a 3B model cannot (AUC 0.29) —
ruling out trivial label leakage and showing detection is capability-gated (§7).
We release the harness, dataset builder, scorer, and all run artifacts. **Headline
numbers (AUC = 1.0) reflect an easy negative class and a small pilot and should not
be read as deployment performance**; the contribution is the method, the honest
evaluation protocol, and the negative-class diagnosis.

---

## 1. Introduction

The scholarly record is under attack from two converging sources. **Paper mills**
sell authorship on fabricated manuscripts at industrial scale — Elsevier alone
recently exposed 24 bad-actor networks spanning ~1,100 members, and the 2026 World
Conference on Research Integrity named GenAI-accelerated fraud the field's top
threat. Simultaneously, **LLM text generation** lets a single actor produce fluent,
plausible-but-unsound papers; the *BadScientist* study showed fabricated manuscripts
achieving acceptance rates up to 82% against automated reviewers.

Detection has not kept pace. The deployed-detector family — Clear Skies'
*Papermill Alarm*, the STM Integrity Hub, Cabanac et al.'s *Problematic Paper
Screener* — keys on **surface signals**: tortured phrases ("bosom peril" for breast
cancer), template leftovers, citation/metadata anomalies. Recent LLM work
(*Pub-Guard-LLM*) frames detection as **retraction classification** with a single
model. Both approaches share a blind spot for fluent fraud and, we argue, a deeper
**evaluation** problem: they are scored against retraction labels whose *negative*
class ("not retracted") is unreliable.

We study `gunting`, an auditor that **decomposes** a paper into nine integrity
dimensions (methodology, results, author, duration, findings, summary, formatting,
inconsistency, plausibility), audits each with an independent web-enabled agent,
and synthesizes a 0–100 fraud-risk score with located, evidence-bearing flags. Our
contributions:

1. **A reproducible, leakage-controlled benchmark** built from Retraction Watch +
   PMC OA full text, with a dataset builder, PMC fetcher, retraction-notice
   sanitizer, pure-Python scorer (AUC, P/R/F1, ECE, bootstrap CIs), and a lexical
   fingerprint baseline. One command reproduces every number; the same harness scales
   to the full ~6,300 fraud-positive corpus.
2. **A clean 2×2 ablation** (decomposition × web) plus baselines, isolating where
   the auditor's design earns its cost.
3. **The negative-class diagnosis**: a demonstration that benchmark difficulty is
   governed almost entirely by how negatives are chosen, and that same-domain
   non-retracted controls are unsafe.
4. **An adversarial arm** against freshly LLM-generated fabrications, testing
   generalization to fraud with no retraction record and no fingerprint.

We are deliberate about scope: this is a **pilot (n = 14)** with an easy negative
class. We report what is real and flag what is not.

---

## 2. Related Work

**Surface / fingerprint detectors.** The Problematic Paper Screener (Cabanac et al.)
flags tortured phrases at scale; Clear Skies' Papermill Alarm and the STM Integrity
Hub combine lexical and metadata/network signals. These are precise on *crude* mills
but, as we show, blind to fluent ones.

**LLM detectors.** *Pub-Guard-LLM* (2025) detects retracted biomedical articles with
three modes (Vanilla Reasoning, RAG, Multi-Agent Debate) over an 11,192-article
corpus (24.5% retracted); reported test-set F1 ≈ 70, average F1 ≈ 76.8 (RAG),
best recall ≈ 88.7 (Debate), beating fine-tuned SciBERT (F1 ≈ 60.9) and few-shot
LLMs (F1 ≈ 30–48). Our auditor differs in **decomposition** (nine specialist
dimensions vs one model) and in producing **located, human-actionable flags**, and
we deliberately separate fraud **reasoning** from retraction **status**.

**Adversarial generation.** *BadScientist* frames the offense — can a generator fool
reviewers? We frame the defense and reuse its premise to build an adversarial test set.

---

## 3. The `gunting` Auditor

Given one paper's text, `gunting` runs nine **web-enabled specialist agents**, one
per integrity dimension, each emitting structured flags
(`severity ∈ {CRITICAL, HIGH, MEDIUM, LOW}`, `claim`, `issue`, `evidence`,
`location`, `sources`, `confidence`) and a 0–100 `dimension_risk`. A synthesizer
aggregates:

> **overall = max(dimension_risk)** if any dimension ≥ 80 (a CRITICAL); **else a
> weighted mean** with integrity dimensions (methodology, results, inconsistency,
> plausibility) weighted ×1.5 and the rest ×1.0.

Labels: 0–19 *clean*, 20–39 *minor*, 40–69 *serious*, 70–100 *likely fraud*. The
aggregation choice matters for calibration (§5.2).

---

## 4. Benchmark Construction

**Positives (reliable).** From the Retraction Watch database (CC0, via Crossref
Labs; 9,374 records in our snapshot), we keep `RetractionNature = Retraction`
records whose `Reason` contains explicit fraud/mill markers (*Paper Mill*, *Fake/
Compromised Peer Review*, *Fabrication*, *Falsification*, *Unreliable Data*, …),
yielding **6,362 fraud positives**; 984 carry a PubMed ID, 733 from Hindawi. We draw
pilot positives from the high-purity *Paper Mill / Fake Peer Review* subset.

**The negative-class problem.** Retraction Watch certifies *positives*; it does not
certify *negatives*. Our first control set — non-retracted PMC papers from the **same
domain and era** (2017–2021 oncology miRNA/lncRNA, the genre mills flooded) — proved
unsafe: a no-rubric model flagged **5 of 7** as suspicious (§5.4). We therefore fix a
**source-quality rule, independent of any score**: controls must come from
high-integrity venues (eLife, Nature Communications, Genome Biology, PLoS Biology)
with mandatory data-availability and rigorous review. This trades realism (the
negatives become *easy*) for label safety, and we report both.

**Full text & leakage control.** Text is fetched from the PMC BioC API. Because PMC
full text for retracted articles can embed a retraction notice — a direct label leak
— we **sanitize** every text, stripping lines that announce retraction/withdrawal/
erratum *status*, and drop any paper whose status cannot be cleanly removed. We also
instruct every web-enabled agent **never to look up the paper's own retraction
status** (Retraction Watch / PubPeer) and to judge only from internal evidence +
factual verification (do authors/journal/citations exist; are values plausible).

**Pilot set.** 14 papers: **6** paper-mill retractions + **8** high-integrity-venue
controls, domain-adjacent (cancer molecular biology), leak-sanitized.

**Configurations (2×2 + baselines).**

| Config | Decomposition | Web | Note |
|---|---|---|---|
| `gunting_web` | 9 dimensions | yes | full system |
| `gunting_noweb` | 9 dimensions | no | web ablation |
| `mono_web` | single holistic | yes | decomposition ablation |
| `vanilla` | single, no rubric | no | LLM floor |
| `fingerprint` | — | — | lexical/structural detector |

All LLM configs use the same model (Claude Opus 4.x). The fingerprint baseline
implements a tortured-phrase lexicon (Problematic-Paper-Screener style) plus
placeholder-citation, template, and citation-density heuristics.

---

## 5. Results

### 5.1 Main benchmark (n = 14; 6 positive / 8 negative)

Decision thresholds: **T40** (≥ "serious") and **T70** (≥ "likely fraud").
95% CIs are 1,000-sample bootstrap.

| Config | AUC (CI) | ECE | T40 P / R / F1 | T70 P / R / F1 |
|---|---|---|---|---|
| **gunting_web**   | **1.00** (1.00–1.00) | 0.19 | 1.00 / 1.00 / **1.00** | 1.00 / 0.17 / 0.29 |
| **gunting_noweb** | **1.00** (1.00–1.00) | 0.17 | 1.00 / 1.00 / **1.00** | 1.00 / 0.67 / 0.80 |
| **mono_web**      | **1.00** (1.00–1.00) | 0.15 | 1.00 / 1.00 / **1.00** | 1.00 / 0.67 / 0.80 |
| **vanilla**       | **1.00** (1.00–1.00) | 0.19 | 1.00 / 0.83 / 0.91 | 1.00 / 0.50 / 0.67 |
| **fingerprint**   | **0.44** (0.30–0.50) | 0.45 | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 |

**Reasoning crushes fingerprinting on fluent mills.** Every reasoning config ranks
all 6 positives above all 8 controls (positives 52–88; controls 3–17). The lexical
detector scores **0 on all 14** papers (AUC 0.44) — the modern oncology mills carry
none of the crude tortured-phrase/placeholder signals it depends on. (Sanity check:
the same detector scores 50 on a *crude* mill case, PMC9420581, confirming it fires
when surface signals exist.)

### 5.2 Ablations: discrimination vs calibration

On this clean-control set, **decomposition and web access do not change AUC** — all
four LLM configs achieve 1.00. The differences are in **operating point**:

- **At T40 (the practical screening threshold), everything works** (F1 0.91–1.00).
- **At T70**, `gunting_web` collapses to recall 0.17, while `gunting_noweb` and
  `mono_web` hold 0.67. Cause: `gunting`'s **weighted-mean aggregation dilutes** a
  paper that has many genuinely-clean dimensions (e.g., *duration*, *author*) unless
  one dimension fires a CRITICAL (≥80). True mills cluster in the *serious* band
  (55–69), correctly suspicious but rarely labeled *likely fraud*.
- **Web access** *lowers* positive scores rather than raising them (e.g., the
  fabricated-CNN paper PMC9499792: 88 no-web → 59 web), because verification confirms
  the journal/refs are real and the auditor moderates. Web thus trades sensitivity
  for **specificity and grounding** — its decisive value appears against fabricated
  citations (§5.5), not on this corpus's AUC.

**Implication:** the contribution of decomposition is **not** higher AUC on easy
negatives; it is (a) **explainability** (located, dimension-attributed flags, §5.3)
and (b) **specificity on hard negatives** — and the default fraud threshold and
aggregation need recalibration (we suggest threshold 40, or counting dimensions in
the *serious+* band, rather than threshold 70).

### 5.3 Which dimensions discriminate, and explainability

Mean dimension scores, positives vs controls (`gunting_web`):

| Dimension | pos | neg | gap |
|---|---|---|---|
| plausibility | 67.2 | 6.5 | **60.7** |
| methodology | 64.7 | 4.5 | **60.2** |
| results | 67.2 | 7.1 | **60.0** |
| inconsistency | 71.5 | 13.2 | **58.2** |
| formatting | 65.8 | 8.6 | 57.2 |
| findings | 61.2 | 5.6 | 55.5 |
| summary | 45.8 | 3.9 | 42.0 |
| author | 43.0 | 2.8 | 40.2 |
| duration | 23.7 | 3.8 | 19.9 |

The four **integrity dimensions** weighted ×1.5 in the synthesizer are exactly the
most discriminative (gaps ~58–61), empirically validating the design; *duration*
contributes least (text-only auditing cannot see submission timelines).

**Explainability vs ground truth.** Without access to retraction status, `gunting`'s
top flags map onto the *documented* Retraction Watch reasons:

| Paper | RW reasons (ground truth) | gunting's independent flags |
|---|---|---|
| PMC7840786 | Paper Mill; Unreliable Data; Concerns about Data | backward miR→FOXO mechanism; no quantitative data; duplicated figure caption |
| PMC7844839 | Paper Mill; Duplication/Plagiarism of Data | template mill family; **false ATCC cell-line provenance**; unquantified blots |
| PMC6910214 | Paper Mill; Concerns/Plagiarism of Image | figure-legend mismatches; mechanistically backwards SKP2 claim; impossible "2–3 s" DAB |
| PMC7656116 | Paper Mill; Concerns about Data/Image | cell-line misclassification; cherry-picked TCGA; **non-existent siRNA vendor** |
| PMC8072314 | Paper Mill; Plagiarism of Data | **phantom "miR-203 inhibitor"** copy-paste; funding/institution mismatch; impossible 500 µM |
| PMC9499792 | Paper Mill; Computer-Generated; Referencing | impossible identical 99.6% metrics; off-topic citation padding; tortured CNN terms |

The flags are *located* and *checkable*, and recover the integrity failures behind
each retraction — the property an editor actually needs.

### 5.4 The negative-class problem (hard negatives)

Re-running the floor model (`vanilla`) on the discarded **same-domain non-retracted**
control set:

- **5 / 7** scored ≥ 40 (serious+); **3 / 7** scored ≥ 70 (likely fraud).

These papers are *not* in Retraction Watch, yet a detector flags most of them. Two
readings are possible and **indistinguishable without ground truth we do not have**:
they are false positives, *or* they are undetected mills (entirely plausible in this
genre and era). Either way, **"non-retracted" is not a valid negative label**, and a
benchmark's apparent difficulty is set almost entirely by how negatives are chosen.
This is, we argue, the central obstacle to honest evaluation of mill detectors — and
a reason published retraction-classification scores should be read cautiously.

### 5.5 Adversarial arm: novel LLM-generated fraud (BadScientist threat)

We generated three papers with an LLM — two **fluent fabrications** (an ML intrusion
detector; a biomedical ceRNA study) and one **honest synthetic control** — and
audited them **blind** with `gunting_web`. None has a retraction record or surface
fingerprint.

| Paper | True | gunting | verdict |
|---|---|---|---|
| ADV1 (fabricated ML) | fraud | **95** | likely_fraud |
| ADV2 (fabricated biomed) | fraud | **82** | likely_fraud |
| ADV_CTRL (honest ML) | clean | **5** | clean |

For ADV1, the auditor **web-verified that the cited journals do not exist** and
proved the headline result (frozen-weight transfer across datasets with incompatible
feature schemas) is *physically impossible*. For ADV2 it caught mirror-image
too-clean fold-changes and the paper's own boast of "uniformly small error bars."
The honest control was cleared after verifying its datasets and citations are real.
This is the case fingerprints and retraction-lookups cannot address, and where
**web-grounded reasoning is decisive**.

---

## 6. Comparison to Pub-Guard-LLM (context, not head-to-head)

Pub-Guard-LLM reports test-set F1 ≈ 70 / avg F1 ≈ 76.8, recall ≈ 88.7, on 11,192
articles at 24.5% prevalence, predicting **retraction**. Our reasoning configs reach
F1 = 1.00 at T40 — but this is **not comparable**: our pilot is small and balanced,
our negatives are *easy* (high-integrity venues), and our target is **fraud reasoning
with status-lookup forbidden**, not retraction prediction. The honest takeaway is
*not* "gunting beats Pub-Guard"; it is that **scores are dominated by negative-class
choice and prevalence**, and that the field needs shared, label-safe negatives before
cross-system numbers mean anything.

---

## 7. Independent replication (offline, non-Claude)

A fair objection to §5: the auditor was Claude, run in sessions that knew the dataset
was retraction-derived (and the same model family generated the §5.5 adversarial set).
Could the separation be a Claude artifact or trivial label leakage in the texts? We
re-ran the core benchmark under strict isolation: papers **anonymized** to opaque ids
with labels hidden; auditor = a **different, fully offline** model that *cannot* query
Retraction Watch or anything else; orchestration mechanical; `overall` recomputed in
Python from the model's dimension scores. Two prompts (decomposed vs holistic), same
scorer/labels/thresholds.

| Auditor (offline, blinded) | decomposed AUC | holistic AUC |
|---|---|---|
| Qwen2.5-3B-Instruct (local) | 0.29 | 0.43 |
| **Qwen3.6-35B-A3B (independent server)** | **0.74** | **0.98** |
| Claude Opus 4.x (§5, for reference) | 1.00 | 1.00 |
| fingerprint (model-free) | — | 0.50 |

Three results. (1) **The finding replicates without Claude and without any web
access**: an independent offline model separates mills from controls at holistic
AUC 0.98 — it is not a Claude artifact and not web leakage. (2) **No trivial label
signal exists in the texts**: the 3B model cannot separate the classes at all
(AUC 0.29, rating everything 80–90); a cheap give-away would let even it win. (3)
**Detection is capability-gated, and decomposition is capability-sensitive** — on the
35B, the 9-dimension rubric *hurts* (0.74 vs 0.98 holistic): per-dimension noise +
weighted-mean dilution + one control false-positive (a Genome Biology paper drew a
spurious dimension spike to 85). On Claude the two are equal (1.0); on weaker models a
holistic prompt is safer. The decomposition's payoff is explainability, not robustness,
and it requires a strong base model. (Reasoning models also need generous output
budgets: one Qwen3.6 audit initially scored 0 from a truncated JSON, 85 on re-run.)
Harness and artifacts: `benchmark/repro/`.

## 8. Limitations (read before citing any number)

- **Pilot size.** n = 14 (6/8). CIs are wide where they matter (T70 F1 CI for
  `gunting_web` is [0.0, 0.67]). The full-corpus run (harness provided) is future work.
- **Easy negatives.** High-integrity-venue controls make AUC = 1.0 unsurprising; the
  honest difficulty lives in §5.4.
- **Genre skew.** Positives are 5 oncology mills + 1 CS paper; controls skew
  biomedical. Generalization across fields is untested.
- **Single model, dual role.** The same model family powers `gunting` *and* generated
  the adversarial set — the adversarial result shows Claude can catch Claude-written
  fraud, not that it generalizes to all generators or that an adversary optimizing
  against `gunting` could not evade it. (§7 partially addresses the auditor side via an
  independent non-Claude replication; the generator side remains single-family.)
- **Residual leakage risk.** Two web-enabled agents reported incidentally seeing a
  retraction mention and stated they ignored it per instructions; we cannot fully
  guarantee no influence. Sanitization + instruction are mitigations, not proofs.
- **No image forensics.** Text-only; image duplication (a top RW reason) is inferred
  indirectly via figure-legend inconsistencies.
- **Reproducibility caveat.** Exact scores are model/version dependent; the harness
  reproduces the *protocol* and data, not bit-identical LLM outputs.

---

## 9. Conclusion

On fluent modern paper mills, **reasoning-based auditing decisively outperforms
surface fingerprinting** (AUC 1.00 vs 0.44), and a decomposed, web-grounded auditor
adds **located, ground-truth-aligned explanations** and **specificity on hard
negatives** — while needing threshold/aggregation recalibration to label fraud
rather than merely "serious concern." It also catches **novel LLM-generated
fabrications** (82–95/100) that have no retraction record or fingerprint, including
by detecting invented citations. But the result that should shape the field is
negative: **retraction-based benchmarks cannot certify their negatives**, so
headline detection scores — ours included — overstate deployment performance. The
next step is a label-safe negative set (adjudicated clean papers, or
prospective-then-confirmed cohorts) and a full-corpus run; the harness to do both is
released here.

---

## Reproducibility

All code, data builders, run artifacts, and the scorer are in `benchmark/`. See
`benchmark/README.md`. The Retraction Watch snapshot is CC0; PMC texts are
open-access. `python3 scoring/score.py --labels sets/labeled.jsonl --run ...`
regenerates every metric in §5.1.

*Artifact and correspondence: gunting-paper-audit.*
