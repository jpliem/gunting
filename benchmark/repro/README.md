# Independent reproduction — offline local-model auditor

Addresses a real contamination worry: the original runs used Claude subagents that
knew the dataset was label-built from Retraction Watch, a couple of agents glimpsed
stray retraction mentions, and the same model family also generated the adversarial
papers. This harness re-runs the core benchmark with an **independent, offline, local
model** so the result cannot depend on Claude's prior knowledge or any web lookup.

## Isolation guarantees

1. **Offline auditor.** The judge is a local Ollama model. It has **no network** — it
   *cannot* query Retraction Watch / PubPeer / the paper's status. The only leakage
   channel in the original (web) is physically removed.
2. **Blinding.** `anonymize.py` renames every paper to an opaque `DOC########` id and
   hides labels in `_keymap.json` (never shown to the model). Directory order is
   label-independent. The model sees text only.
3. **Mechanical orchestration.** Claude Code (or any driver) only runs scripts:
   anonymize → call local model → compute scores → run the scorer. No judgment by the
   orchestrator. The aggregation (`overall`) is computed in Python from the model's
   dimension scores via gunting's exact formula, so the orchestrator's opinions can't
   enter the numbers.
4. **No status strings in text.** Inputs are the already-sanitized `text_clean.txt`
   (retraction notices stripped), head-truncated to fit the local context window.

## Run

```bash
ollama serve &                      # start local server
./run.sh qwen2.5:3b-instruct        # or any local model you trust
cat runs/results_local.json
```

Steps (see `run.sh`): blind → fingerprint baseline → local decomposed audit →
local holistic audit → score against blind labels.

## What this tests

Not "does a 3B model match Opus" (it won't — capability differs). It tests whether
the **qualitative finding replicates** with a model that has no foreknowledge:
- Does reasoning-based scoring separate the RW positives from controls at all?
- Does the model-free fingerprint baseline still fail?
- Does the ranking hold without any web access or Claude involvement?

Swap in a stronger local model (e.g. `qwen2.5:7b-instruct`, `llama3.1:8b`) on bigger
hardware for a closer capability comparison. Results land in `runs/results_local.json`
and are directly comparable to the parent `scoring/results.json` (same scorer, same
thresholds, same labels).

## Files
- `anonymize.py` — blind the pilot, write `_keymap.json` (kept from the model)
- `local_audit.py` — offline Ollama auditor (decomposed `gunting` / holistic `vanilla`)
- `run.sh` — end-to-end
- `runs/` — local model outputs + `results_local.json`
