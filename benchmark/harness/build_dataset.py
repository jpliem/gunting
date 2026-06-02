#!/usr/bin/env python3
"""Build a labeled paper-mill / fabrication benchmark from the Retraction Watch dataset.

Source of truth for labels: the Retraction Watch Database, published CC0 via Crossref
Labs (https://api.labs.crossref.org/data/retractionwatch). Positives = papers retracted
for fraud/paper-mill reasons. Negatives = contemporaneous non-retracted controls.

No third-party deps (stdlib csv/json/re only) so it runs on a bare Python 3.

Usage:
    python3 build_dataset.py --rw data/retraction_watch.csv --out sets/candidates.jsonl
"""
import argparse, csv, json, re, sys
from collections import Counter

# Retraction reasons that indicate fabrication / paper-mill / integrity fraud
# (matched case-insensitively as substrings of the RW "Reason" field).
FRAUD_REASONS = [
    "paper mill",
    "fake peer review",
    "concerns/issues about authorship",
    "concerns/issues with peer review",
    "fabrication",
    "falsification",
    "manipulation of results",
    "manipulation of images",
    "unreliable results",
    "unreliable data",
    "euphemism for misconduct",
    "forged authorship",
    "rogue editor",
    "concerns about authenticity",
    "randomly generated content",
    "fake affiliation",
    "bought authorship",
]

# Reasons that are NOT integrity-fraud (honest error, duplication-by-author,
# legal, etc.) — used to keep the positive class clean.
NON_FRAUD_ONLY = [
    "error in",
    "duplication of article",  # self-duplication, not mill, when alone
    "withdrawal",
    "publisher error",
    "copyright claims",
    "legal reasons",
    "notice - lack of",
]

csv.field_size_limit(10_000_000)


def reason_is_fraud(reason: str) -> bool:
    r = reason.lower()
    return any(k in r for k in FRAUD_REASONS)


def parse_pmid(v: str) -> str:
    v = (v or "").strip()
    return v if v.isdigit() and v != "0" else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=0, help="cap rows scanned (0=all)")
    args = ap.parse_args()

    reason_counter = Counter()
    pos = []
    n = 0
    with open(args.rw, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        # RW column names have drifted over versions; resolve defensively.
        def col(*names):
            for nm in names:
                for c in cols:
                    if c.strip().lower() == nm.lower():
                        return c
            return None
        C = {
            "title":  col("Title"),
            "reason": col("Reason"),
            "nature": col("RetractionNature"),
            "subj":   col("Subject"),
            "journal":col("Journal"),
            "pub":    col("Publisher"),
            "country":col("Country"),
            "odoi":   col("OriginalPaperDOI"),
            "opmid":  col("OriginalPaperPubMedID"),
            "odate":  col("OriginalPaperDate"),
            "rdate":  col("RetractionDate"),
        }
        if not C["reason"]:
            print(f"FATAL: no Reason column. cols={cols}", file=sys.stderr)
            sys.exit(1)
        for row in reader:
            n += 1
            if args.max and n > args.max:
                break
            nature = (row.get(C["nature"]) or "").strip().lower()
            if nature and nature != "retraction":
                continue  # skip expressions-of-concern / corrections
            reason = row.get(C["reason"]) or ""
            for part in re.split(r"[+;]", reason):
                p = part.strip()
                if p:
                    reason_counter[p] += 1
            if not reason_is_fraud(reason):
                continue
            doi = (row.get(C["odoi"]) or "").strip()
            pmid = parse_pmid(row.get(C["opmid"]) or "")
            if not doi and not pmid:
                continue
            pos.append({
                "label": 1,
                "label_reason": reason.strip(),
                "title": (row.get(C["title"]) or "").strip(),
                "doi": doi,
                "pmid": pmid,
                "journal": (row.get(C["journal"]) or "").strip(),
                "publisher": (row.get(C["pub"]) or "").strip(),
                "country": (row.get(C["country"]) or "").strip(),
                "orig_date": (row.get(C["odate"]) or "").strip(),
                "retraction_date": (row.get(C["rdate"]) or "").strip(),
                "source": "retraction_watch",
            })

    with open(args.out, "w", encoding="utf-8") as out:
        for rec in pos:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"scanned {n} RW rows; {len(pos)} fraud/mill positives written -> {args.out}")
    print("top 25 reason tokens seen:")
    for r, c in reason_counter.most_common(25):
        print(f"  {c:6d}  {r}")


if __name__ == "__main__":
    main()
