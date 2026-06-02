#!/usr/bin/env python3
"""Resolve a paper id (PMID/PMCID/DOI) to PMC open-access full text and write it in
the layout gunting expects: <out>/text.txt (section/page markers) + <out>/meta.json.

Uses only stdlib (urllib). NCBI BioC API for full text; NCBI ID converter for PMID->PMCID.

Usage:
    python3 fetch_text.py --pmcid PMC9420581 --out ../runs/_text/PMC9420581
    python3 fetch_text.py --pmid 35... --out ...
"""
import argparse, json, os, sys, time, urllib.request, urllib.parse

UA = "gunting-benchmark/1.0 (mailto:vio.intelligent@gmail.com)"
EMAIL = "vio.intelligent@gmail.com"


def _get(url, tries=3, sleep=1.0):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(sleep * (i + 1))
    return ""


def pmid_to_pmcid(pmid):
    url = ("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids="
           f"{pmid}&format=json&tool=gunting&email={urllib.parse.quote(EMAIL)}")
    try:
        data = json.loads(_get(url))
        recs = data.get("records", [])
        if recs and recs[0].get("pmcid"):
            return recs[0]["pmcid"]
    except Exception:
        pass
    return ""


def doi_to_pmcid(doi):
    url = ("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids="
           f"{urllib.parse.quote(doi)}&format=json&tool=gunting&email={urllib.parse.quote(EMAIL)}")
    try:
        data = json.loads(_get(url))
        recs = data.get("records", [])
        if recs and recs[0].get("pmcid"):
            return recs[0]["pmcid"]
    except Exception:
        pass
    return ""


def fetch_bioc(pmcid):
    pid = pmcid.replace("PMC", "")
    url = ("https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
           f"BioC_json/PMC{pid}/unicode")
    raw = _get(url)
    doc = json.loads(raw)
    # BioC json: list[ {documents:[ {passages:[ {text, infons:{section_type,type}} ]} ]} ]
    if isinstance(doc, list):
        doc = doc[0]
    out, cur_sec = [], None
    title = ""
    for d in doc.get("documents", []):
        for p in d.get("passages", []):
            infons = p.get("infons", {})
            sec = infons.get("section_type") or infons.get("type") or ""
            txt = (p.get("text") or "").strip()
            if not txt:
                continue
            if infons.get("type", "").lower() == "title" and not title:
                title = txt
            if sec != cur_sec:
                out.append(f"===== SECTION {sec or 'BODY'} =====")
                cur_sec = sec
            out.append(txt)
    return "\n".join(out), title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmcid")
    ap.add_argument("--pmid")
    ap.add_argument("--doi")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", type=int, default=-1)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    pmcid = args.pmcid or ""
    if not pmcid and args.pmid:
        pmcid = pmid_to_pmcid(args.pmid)
    if not pmcid and args.doi:
        pmcid = doi_to_pmcid(args.doi)
    if not pmcid:
        print("NO_PMCID", file=sys.stderr)
        sys.exit(3)

    try:
        text, title = fetch_bioc(pmcid)
    except Exception as e:
        print(f"FETCH_FAIL {pmcid}: {e}", file=sys.stderr)
        sys.exit(4)

    chars = len(text)
    if chars < 500:
        print(f"TOO_SHORT {pmcid} ({chars} chars)", file=sys.stderr)
        sys.exit(5)

    os.makedirs(os.path.join(args.out, "findings"), exist_ok=True)
    with open(os.path.join(args.out, "text.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    meta = {
        "source_pdf": f"(BioC full text from {pmcid})",
        "title": title, "author": "", "doi": args.doi or "",
        "pmcid": pmcid, "pmid": args.pmid or "",
        "pages": 0, "chars": chars, "extracted_with": "pmc-bioc-api",
        "label": args.label, "note": args.note,
    }
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"OK {pmcid} {chars} chars -> {args.out}")


if __name__ == "__main__":
    main()
