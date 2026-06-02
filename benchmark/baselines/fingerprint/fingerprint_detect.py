#!/usr/bin/env python3
"""Fingerprint baseline: lexical / structural paper-mill detector.

Mimics the deployed-detector family (Cabanac et al. "Problematic Paper Screener",
Clear Skies "Papermill Alarm"-style surface signals). Pure stdlib; no LLM, no web.
Produces a 0-100 risk score per paper from:
  1. Tortured phrases (established lexicon of synonym-swapped technical terms).
  2. Placeholder / broken citation patterns ("in reference [ ]", numberless refs).
  3. Template/boilerplate artifacts.
  4. Mill-correlated surface stats (citation-density anomalies).

This is intentionally a *surface* detector — the benchmark's point is to compare it
against reasoning-based auditing.

Usage: python3 fingerprint_detect.py --labels ../../sets/labeled.jsonl --out ../../runs/fingerprint.jsonl
"""
import argparse, json, re

# Established tortured phrases (subset of the public Problematic Paper Screener lexicon;
# each maps a mangled phrase -> the real term it replaced).
TORTURED = [
    "bosom peril", "bosom malignant growth", "bosom disease",        # breast cancer
    "counterfeit consciousness", "counterfeit neural",               # artificial intelligence/NN
    "irregular esteem", "arbitrary esteem",                          # random value
    "lung malignancy",                                               # not tortured but watched
    "leukemia disease",
    "colossal information", "huge information",                      # big data
    "信息 noise",
    "mean square blunder", "mean squared blunder",                   # mean square error
    "motion estimation -> movement estimation",
    "remaining vitality", "leftover vitality",                       # residual energy
    "underlying foundations",                                        # roots
    "glucose tolerance -> glucose resistance",
    "false positive -> bogus positive", "bogus positive",            # false positive
    "false negative -> bogus negative", "bogus negative",            # false negative
    "deep learning -> profound learning", "profound learning",       # deep learning
    "support vector machine -> help vector machine", "help vector",  # SVM
    "cloud computing -> haze figuring",                              # cloud computing
    "signal to noise ratio -> flag to clamor proportion", "flag to clamor",
    "neural network -> neural organization", "brain organization",   # neural network
    "data set -> informational index",                               # dataset
    "convolutional -> convolutional brain",
    "name a few -> name a couple", "name a couple",
    "home and abroad -> Japan and abroad",                           # mangled idiom (seen in PMC9420581)
]
# Normalize: keep only the mangled side
TORTURED = [t.split("->")[-1].strip() for t in TORTURED]
TORTURED = [t for t in TORTURED if t and " " in t or len(t) > 6]

PLACEHOLDER_CITE = [
    r"in reference\s*[_\[]?\s*[_\]\.]",      # "in reference ___" / "in reference [ ]"
    r"reference\s+proposes",
    r"\bin document\b",
    r"\bliterature,\s*literature\b",
    r"method in reference\s*_+",
    r"\[\s*\?+\s*\]",                          # [?] placeholders
    r"\bcitation needed\b",
    r"reference\s+\[\s*\]",                    # empty bracket ref
]
TEMPLATE_ARTIFACTS = [
    r"\b(insert|enter)\s+(your|the)\s+\w+\s+here\b",
    r"\bAuthor\s+\d+\b",
    r"\bXXXX+\b",
    r"\blorem ipsum\b",
    r"use style paper title",
    r"\bTODO\b",
]


def detect(text):
    low = text.lower()
    hits = {"tortured": [], "placeholder_cite": 0, "template": 0}
    for t in TORTURED:
        if t in low:
            hits["tortured"].append(t)
    for pat in PLACEHOLDER_CITE:
        hits["placeholder_cite"] += len(re.findall(pat, low))
    for pat in TEMPLATE_ARTIFACTS:
        hits["template"] += len(re.findall(pat, low, re.I))
    # citation-density anomaly: numbered refs present but near-zero in-text [n] markers
    ref_list = len(re.findall(r"^\s*\[?\d{1,3}\]?[\.\)]\s", text, re.M))
    intext = len(re.findall(r"\[\d{1,3}\]", text))
    cite_anom = 1 if (ref_list >= 10 and intext < 3) else 0
    hits["cite_density_anomaly"] = cite_anom

    # Score: each signal class capped, summed, scaled to 0-100.
    s = 0
    s += min(len(hits["tortured"]) * 25, 60)        # tortured phrases are strong
    s += min(hits["placeholder_cite"] * 20, 50)
    s += min(hits["template"] * 20, 40)
    s += cite_anom * 25
    score = min(s, 100)
    return score, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = []
    with open(args.labels) as f:
        for line in f:
            r = json.loads(line)
            text = open(f"{r['dir']}/text.txt", encoding="utf-8").read()
            score, hits = detect(text)
            out.append({"id": r["id"], "score": score, "label_true": r["label"],
                        "signals": {"tortured": hits["tortured"],
                                    "placeholder_cite": hits["placeholder_cite"],
                                    "template": hits["template"],
                                    "cite_density_anomaly": hits["cite_density_anomaly"]}})
    with open(args.out, "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"fingerprint baseline -> {args.out} ({len(out)} papers)")
    for r in out:
        print(f"  {r['id']:<14} score {r['score']:>3}  label {r['label_true']}  "
              f"tortured={len(r['signals']['tortured'])} "
              f"ph_cite={r['signals']['placeholder_cite']} "
              f"tmpl={r['signals']['template']} cda={r['signals']['cite_density_anomaly']}")


if __name__ == "__main__":
    main()
