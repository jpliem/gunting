#!/usr/bin/env bash
# Independent, blinded, OFFLINE reproduction of the gunting benchmark.
# Auditor = a LOCAL Ollama model (no internet; cannot look up retraction status).
# Orchestration is mechanical; no judgment by the orchestrator.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${1:-qwen2.5:3b-instruct}"
echo "== model: $MODEL =="

# 1. Blind the pilot (anonymize ids, head-truncate, hide labels)
python3 anonymize.py --labels ../sets/labeled.jsonl --maxchars 16000
python3 -c "import json;km=json.load(open('_keymap.json'));open('_labels_blind.jsonl','w').write('\n'.join(json.dumps({'id':b,'label':v['label']}) for b,v in km.items())+'\n')"

# 2. Model-free fingerprint baseline on blind texts
python3 - <<'PY'
import sys,glob,os,json; sys.path.insert(0,'../baselines/fingerprint')
from fingerprint_detect import detect
out=[{'id':os.path.splitext(os.path.basename(f))[0],'score':detect(open(f).read())[0]} for f in sorted(glob.glob('blind/*.txt'))]
open('runs/fingerprint.jsonl','w').write('\n'.join(json.dumps(r) for r in out)+'\n')
PY

# 3. Local-model auditor: decomposed (gunting) + holistic (vanilla), OFFLINE
python3 local_audit.py --model "$MODEL" --config gunting --out "runs/local_gunting.jsonl"
python3 local_audit.py --model "$MODEL" --config vanilla --out "runs/local_vanilla.jsonl"

# 4. Score against blind labels (de-anonymization happens only here, in the scorer's eyes)
python3 ../scoring/score.py --labels _labels_blind.jsonl \
  --run local_gunting=runs/local_gunting.jsonl \
  --run local_vanilla=runs/local_vanilla.jsonl \
  --run fingerprint=runs/fingerprint.jsonl \
  --thresholds 40,70 --out runs/results_local.json
echo "== done: runs/results_local.json =="
