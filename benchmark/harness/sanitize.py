#!/usr/bin/env python3
"""Strip retraction-status leakage from pilot texts so detection configs cannot cheat
by reading an embedded retraction notice. Removes whole lines that announce
retraction/withdrawal/erratum STATUS (not ordinary uses of the words in methods).

Writes text_clean.txt next to text.txt and rewrites sets/labeled.jsonl to point at it.
Drops any id in --drop. Reports how many lines were removed per paper.
"""
import argparse, json, re

# Lines announcing publication-integrity status of *this* article.
LEAK_LINE = re.compile(
    r"(this article has been retracted|has been retracted|retracted article|"
    r"retraction note|notice of retraction|^retracted[:\s]|expression of concern|"
    r"this article has been withdrawn|^correction to|^erratum\b|^retraction\b)",
    re.I)


def clean_text(text):
    kept, removed = [], 0
    for line in text.splitlines():
        if LEAK_LINE.search(line.strip()):
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--drop", default="", help="comma-separated ids to drop")
    args = ap.parse_args()
    drop = {x.strip() for x in args.drop.split(",") if x.strip()}

    recs = [json.loads(l) for l in open(args.labels) if l.strip()]
    out_recs = []
    for r in recs:
        if r["id"] in drop:
            print(f"DROP {r['id']}")
            continue
        raw = open(f"{r['dir']}/text.txt", encoding="utf-8").read()
        cleaned, removed = clean_text(raw)
        with open(f"{r['dir']}/text_clean.txt", "w", encoding="utf-8") as f:
            f.write(cleaned)
        r["text"] = f"{r['dir']}/text_clean.txt"
        r["chars_clean"] = len(cleaned)
        out_recs.append(r)
        print(f"{r['id']:<14} label{r['label']} removed {removed} leak line(s)  "
              f"{len(raw)}->{len(cleaned)} chars")

    with open(args.labels, "w") as f:
        for r in out_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    pos = sum(r["label"] for r in out_recs)
    print(f"\nfinal pilot: {len(out_recs)} papers  ({pos} pos / {len(out_recs)-pos} neg)")


if __name__ == "__main__":
    main()
