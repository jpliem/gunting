# Independent reproduction — results

**Question.** The original benchmark ran the auditor as Claude subagents that knew the
dataset was retraction-derived (and the same family wrote the adversarial papers).
Could the separation be a Claude artifact, or trivial label leakage in the texts?

**Method.** Re-ran the *core* benchmark with **independent, offline, blinded** models:
- Papers anonymized to opaque `DOC########` ids, labels hidden, head-truncated to 16k chars.
- Auditor = a local/remote model that **cannot reach the internet** (no Retraction Watch lookup possible).
- Orchestration mechanical; `overall` computed in Python from the model's dimension scores.
- Two prompts: `gunting` (decomposed 9-dimension) and `vanilla` (single holistic 0–100).
- Same scorer, same thresholds, same labels as the parent benchmark.

## Headline

| Model (offline, blinded) | `gunting` AUC | `vanilla` AUC | notes |
|---|---|---|---|
| Qwen2.5-3B-Instruct (local) | 0.29 | 0.43 | flags everything 80–90; no discrimination |
| **Qwen3.6-35B-A3B (remote llama.cpp)** | **0.74** | **0.98** | independent of Claude |
| Claude Opus 4.x (original run) | 1.00 | 1.00 | parent benchmark |
| fingerprint (model-free) | 0.50 | — | unchanged; fails on fluent mills |

Detail (Qwen3.6-35B, n=14, 6 pos / 8 neg):
- `vanilla`: AUC **0.98**, ECE 0.15, T40 P/R/F1 **0.83/0.83/0.83**, T70 **1.00/0.83/0.91**.
- `gunting`: AUC **0.74**, ECE 0.21, T40 **0.80/0.67/0.73**; pos mean 55.7 vs neg mean 24.6 (sep **+31**).

## What this establishes

1. **The finding replicates without Claude.** An independent, offline, blinded
   non-Claude model (Qwen3.6-35B) separates paper-mill positives from
   reputable-venue controls at **AUC 0.98** (holistic). The original result is **not
   a Claude artifact and not web leakage** (the model had no internet).

2. **No trivial label signal in the texts.** The blinded 3B model could not separate
   the classes at all (AUC 0.29, rates everything ~80–90). If the sanitized texts
   carried a cheap give-away, even a weak model would exploit it. They don't — the
   task requires genuine reasoning.

3. **Detection is capability-gated.** 3B ≈ chance → 35B strong → Opus saturates.
   Mill-vs-legit discrimination scales with base-model capability.

4. **Decomposition is capability-sensitive — a real, non-obvious result.** On Claude
   (very strong) the 9-dimension decomposition ≈ holistic (both AUC 1.0). On the
   35B, decomposition *hurts* (0.74 vs 0.98): per-dimension scoring is noisier on a
   weaker model, the weighted-mean dilutes, and one control (PMC9746098, Genome
   Biology) drew a spurious dimension spike (overall 85, a false positive). The
   elaborate pipeline's payoff — located, attributable flags — comes with a
   robustness cost that only a strong-enough base model absorbs. On weaker models, a
   **holistic prompt is the safer choice**.

## Caveats
- n=14 pilot; easy (reputable-venue) negatives. Same limitations as the parent study.
- One Qwen3.6 `gunting` paper initially scored 0 from a JSON truncation (reasoning
  consumed the token budget); re-run with a larger budget → 85. Reasoning models need
  generous `max_tokens` for the structured-output contract.
- Qwen3.6 is a reasoning model; `enable_thinking:false` / `/no_think` were **not**
  honored by this build — it always reasons (~40 s/paper here). Scores use the final
  answer only (reasoning tokens ignored).
- Texts were sent to the operator's own remote server (public PMC OA / Retraction
  Watch data — not sensitive).

## Reproduce
```bash
# local (small model)
ollama serve & ./run.sh qwen2.5:3b-instruct
# remote (OpenAI-compatible llama.cpp)
BASE=https://your-server MODEL=your-model python3 remote_audit.py --config gunting --out runs/remote_gunting.jsonl --think
BASE=... MODEL=... python3 remote_audit.py --config vanilla --out runs/remote_vanilla.jsonl --think
python3 ../scoring/score.py --labels _labels_blind.jsonl --run g=runs/remote_gunting.jsonl --run v=runs/remote_vanilla.jsonl --thresholds 40,70
```
Artifacts: `runs/results_remote.json`, `runs/results_local.json`, `runs/remote_*.jsonl`, `runs/local_*.jsonl`.
