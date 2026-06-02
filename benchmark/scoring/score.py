#!/usr/bin/env python3
"""Score gunting / baseline runs against ground-truth labels.

Pure stdlib (no numpy/sklearn). Computes, per config:
  - confusion matrix, precision, recall (sensitivity), specificity, F1, accuracy
    at decision thresholds (default 40 = "serious concerns or worse", 70 = "likely fraud")
  - ROC-AUC (rank-based Mann-Whitney estimator)
  - Calibration: reliability bins + Expected Calibration Error (ECE)
  - 95% bootstrap CIs for F1 and AUC

Inputs:
  --labels  sets/labeled.jsonl   records: {"id","label"(0/1)}
  --run     runs/<config>.jsonl  records: {"id","score"(0-100)[,"pred_label"]}
  --thresholds 40,70
  --out     scoring/<config>.json   (machine-readable result)

Multiple --run accepted; prints a comparison table.
"""
import argparse, json, math, random

random.seed(20260602)  # deterministic CIs (no Date/random nondeterminism)


def load_jsonl(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def metrics_at(pairs, thr):
    # pairs: list of (label, score)
    tp = fp = tn = fn = 0
    for y, s in pairs:
        pred = 1 if s >= thr else 0
        if y == 1 and pred == 1: tp += 1
        elif y == 0 and pred == 1: fp += 1
        elif y == 0 and pred == 0: tn += 1
        else: fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc  = (tp + tn) / len(pairs) if pairs else 0.0
    return dict(threshold=thr, tp=tp, fp=fp, tn=tn, fn=fn,
                precision=round(prec, 4), recall=round(rec, 4),
                specificity=round(spec, 4), f1=round(f1, 4), accuracy=round(acc, 4))


def auc(pairs):
    # Mann-Whitney U / (n_pos*n_neg). Handles ties at 0.5.
    pos = [s for y, s in pairs if y == 1]
    neg = [s for y, s in pairs if y == 0]
    if not pos or not neg:
        return None
    wins = 0.0
    for ps in pos:
        for ns in neg:
            if ps > ns: wins += 1
            elif ps == ns: wins += 0.5
    return wins / (len(pos) * len(neg))


def ece(pairs, bins=10):
    # scores are 0-100 -> treat /100 as predicted P(fraud). Expected Calibration Error.
    n = len(pairs)
    if n == 0:
        return None, []
    buckets = [[] for _ in range(bins)]
    for y, s in pairs:
        p = min(max(s / 100.0, 0.0), 0.999999)
        buckets[int(p * bins)].append((y, p))
    e = 0.0
    rel = []
    for i, b in enumerate(buckets):
        if not b:
            rel.append(dict(bin=i, n=0, conf=None, acc=None))
            continue
        conf = sum(p for _, p in b) / len(b)
        accv = sum(y for y, _ in b) / len(b)
        e += (len(b) / n) * abs(accv - conf)
        rel.append(dict(bin=i, lo=round(i/bins,2), hi=round((i+1)/bins,2),
                        n=len(b), conf=round(conf, 3), acc=round(accv, 3)))
    return round(e, 4), rel


def f1_at_thr(pairs, thr):
    return metrics_at(pairs, thr)["f1"]


def bootstrap_ci(pairs, fn, n=1000):
    if len(pairs) < 3:
        return None
    vals = []
    N = len(pairs)
    for _ in range(n):
        sample = [pairs[random.randrange(N)] for _ in range(N)]
        v = fn(sample)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals)) - 1]
    return [round(lo, 4), round(hi, 4)]


def score_run(labels, run, thresholds):
    lab = {r["id"]: int(r["label"]) for r in labels}
    pairs, missing = [], []
    for r in run:
        if r["id"] in lab and r.get("score") is not None:
            pairs.append((lab[r["id"]], float(r["score"])))
    covered = {r["id"] for r in run}
    for i in lab:
        if i not in covered:
            missing.append(i)
    res = {
        "n": len(pairs),
        "n_pos": sum(1 for y, _ in pairs if y == 1),
        "n_neg": sum(1 for y, _ in pairs if y == 0),
        "missing_ids": missing,
        "auc": (round(auc(pairs), 4) if auc(pairs) is not None else None),
        "auc_ci95": bootstrap_ci(pairs, auc),
        "thresholds": {},
    }
    e, rel = ece(pairs)
    res["ece"] = e
    res["reliability"] = rel
    for t in thresholds:
        m = metrics_at(pairs, t)
        m["f1_ci95"] = bootstrap_ci(pairs, lambda p, _t=t: f1_at_thr(p, _t))
        res["thresholds"][str(t)] = m
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--run", action="append", required=True, help="config_name=path")
    ap.add_argument("--thresholds", default="40,70")
    ap.add_argument("--out")
    args = ap.parse_args()

    labels = load_jsonl(args.labels)
    thresholds = [int(x) for x in args.thresholds.split(",")]
    all_res = {}
    for spec in args.run:
        name, path = spec.split("=", 1)
        run = load_jsonl(path)
        all_res[name] = score_run(labels, run, thresholds)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(all_res, f, indent=2)

    # pretty comparison
    print(f"{'config':<22}{'n':>4}{'AUC':>8}{'ECE':>7}", end="")
    for t in thresholds:
        print(f"  |  T{t}: P/R/F1", end="")
    print()
    for name, r in all_res.items():
        print(f"{name:<22}{r['n']:>4}{(r['auc'] if r['auc'] is not None else 0):>8}{(r['ece'] if r['ece'] is not None else 0):>7}", end="")
        for t in thresholds:
            m = r["thresholds"][str(t)]
            print(f"  |  {m['precision']:.2f}/{m['recall']:.2f}/{m['f1']:.2f}", end="")
        print()
    if args.out:
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
