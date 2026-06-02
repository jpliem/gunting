#!/usr/bin/env python3
"""Blind the pilot for independent reproduction.

Copies each sanitized paper to repro/blind/<opaque-id>.txt (head-truncated to fit a
small local model's context) and writes repro/_keymap.json mapping opaque-id -> real
id + label. The keymap is NEVER shown to the auditor model. Deterministic (seeded);
no Date/random-at-runtime dependence beyond a fixed seed.

Usage: python3 anonymize.py --labels ../sets/labeled.jsonl --maxchars 16000
"""
import argparse, json, hashlib, os

def opaque(real_id, salt="gunting-repro-2026"):
    h = hashlib.sha256((salt + real_id).encode()).hexdigest()
    return "DOC" + h[:8].upper()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--maxchars", type=int, default=16000)
    ap.add_argument("--outdir", default="blind")
    ap.add_argument("--keymap", default="_keymap.json")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    recs = [json.loads(l) for l in open(args.labels) if l.strip()]
    # stable order independent of label so directory listing leaks nothing
    recs.sort(key=lambda r: opaque(r["id"]))
    keymap = {}
    for r in recs:
        bid = opaque(r["id"])
        # text path: labeled.jsonl stores 'text' (clean) or fall back to dir
        tpath = r.get("text") or f"{r['dir']}/text_clean.txt"
        # resolve relative to benchmark/ (labels paths are relative to benchmark dir)
        if not os.path.isabs(tpath):
            tpath = os.path.join("..", tpath)
        text = open(tpath, encoding="utf-8").read()
        truncated = text[:args.maxchars]
        with open(os.path.join(args.outdir, bid + ".txt"), "w", encoding="utf-8") as f:
            f.write(truncated)
        keymap[bid] = {"real_id": r["id"], "label": r["label"],
                       "chars_used": len(truncated), "chars_total": len(text)}
    with open(args.keymap, "w") as f:
        json.dump(keymap, f, indent=2)
    pos = sum(v["label"] for v in keymap.values())
    print(f"blinded {len(keymap)} papers -> {args.outdir}/ ({pos} pos / {len(keymap)-pos} neg)")
    print(f"keymap -> {args.keymap} (NOT exposed to auditor)")
    trunc = sum(1 for v in keymap.values() if v['chars_used'] < v['chars_total'])
    print(f"{trunc}/{len(keymap)} papers head-truncated to {args.maxchars} chars")

if __name__ == "__main__":
    main()
