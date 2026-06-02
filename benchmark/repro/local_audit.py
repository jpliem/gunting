#!/usr/bin/env python3
"""Offline local-model auditor for independent reproduction.

Runs against a LOCAL Ollama model (no internet — the model physically cannot look up
Retraction Watch / the paper's status). Reads anonymized blind/*.txt, never sees the
real id or label. The model returns 9 dimension scores (0-100); THIS SCRIPT computes
the overall via gunting's exact aggregation formula (so small-model arithmetic can't
distort it). Two configs:
  --config gunting : decomposed 9-dimension rubric
  --config vanilla : single holistic "fraud 0-100" (we still derive overall from it)

Usage:
  python3 local_audit.py --model qwen2.5:3b-instruct --config gunting --out runs/local_gunting.jsonl
"""
import argparse, glob, json, os, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
DIMS = ["methodology","results","author","duration","findings","summary",
        "formatting","inconsistency","plausibility"]
INTEGRITY = {"methodology","results","inconsistency","plausibility"}

GUNTING_SYS = (
 "You are a research-paper fraud auditor. You judge ONLY from the text shown. "
 "You have NO internet and must NOT assume any external knowledge about whether this "
 "paper was retracted. Score each of 9 integrity dimensions 0-100 (0=clean, 100=clear "
 "fraud/fabrication/paper-mill signal):\n"
 "methodology(design/reproducibility/methods-support-claims), results(data&stat integrity, "
 "figure-text consistency, too-clean/impossible numbers), author(affiliation reality, mill "
 "authorship signals visible in text), duration(timeline feasibility vs scope), findings("
 "conclusions supported by data, overclaiming), summary(abstract matches body), formatting("
 "tortured phrases, template artifacts, citation anomalies), inconsistency(internal "
 "contradictions, sample/number drift), plausibility(unrealistic/impossible claims).\n"
 "Output ONLY a JSON object with integer fields for each of the 9 dimensions. No prose.")

VANILLA_SYS = (
 "You screen research papers. Judging ONLY from the text (no internet, no outside "
 "knowledge), output ONLY a JSON object {\"fraud_score\": <0-100 integer>} where 0=clearly "
 "legitimate and 100=clearly fraudulent/paper-mill.")

def gunting_overall(dims):
    if any(v >= 80 for v in dims.values()):
        return max(dims.values())
    num = sum(v*(1.5 if k in INTEGRITY else 1.0) for k,v in dims.items())
    den = sum(1.5 if k in INTEGRITY else 1.0 for k in dims)
    return round(num/den)

def call(model, system, user, num_ctx):
    body = {"model": model, "stream": False, "format": "json",
            "options": {"temperature": 0, "num_ctx": num_ctx},
            "messages": [{"role":"system","content":system},
                         {"role":"user","content":user}]}
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--config", choices=["gunting","vanilla"], required=True)
    ap.add_argument("--blind", default="blind")
    ap.add_argument("--out", required=True)
    ap.add_argument("--num_ctx", type=int, default=8192)
    args = ap.parse_args()
    sys_prompt = GUNTING_SYS if args.config=="gunting" else VANILLA_SYS
    files = sorted(glob.glob(os.path.join(args.blind, "*.txt")))
    out = []
    for fp in files:
        bid = os.path.splitext(os.path.basename(fp))[0]
        text = open(fp, encoding="utf-8").read()
        user = f"PAPER:\n{text}"
        try:
            raw = call(args.model, sys_prompt, user, args.num_ctx)
            obj = json.loads(raw)
        except Exception as e:
            print(f"{bid} FAIL {str(e)[:60]} -> score 0");
            out.append({"id":bid,"score":0,"error":str(e)[:80]}); continue
        if args.config=="gunting":
            dims = {}
            for d in DIMS:
                v = obj.get(d, 0)
                try: v=int(round(float(v)))
                except: v=0
                dims[d]=max(0,min(100,v))
            score = gunting_overall(dims)
            out.append({"id":bid,"score":score,"dimensions":dims})
        else:
            try: score=max(0,min(100,int(round(float(obj.get("fraud_score",0))))))
            except: score=0
            out.append({"id":bid,"score":score})
        print(f"{bid} score {out[-1]['score']}")
    with open(args.out,"w") as f:
        for r in out: f.write(json.dumps(r)+"\n")
    print(f"\nwrote {args.out} ({len(out)} papers, model={args.model}, config={args.config})")

if __name__ == "__main__":
    main()
