#!/usr/bin/env python3
"""Remote-model auditor (OpenAI-compatible llama.cpp server) for independent reproduction.

Same contract as local_audit.py: reads anonymized blind/*.txt (no real id, no label),
returns 9 dimension scores; THIS SCRIPT computes `overall` via gunting's formula.
Handles llama.cpp reasoning models: streams and keeps only `delta.content`
(ignores `reasoning_content`), then extracts the last {...} JSON object.

Usage:
  BASE=https://llamacpp.iotech.my.id MODEL=qwen35 \
  python3 remote_audit.py --config gunting --out runs/remote_gunting.jsonl [--think]
"""
import argparse, glob, json, os, re, urllib.request

BASE = os.environ.get("BASE", "https://llamacpp.iotech.my.id").rstrip("/")
MODEL = os.environ.get("MODEL", "qwen35")
KEY = os.environ.get("LLAMA_KEY", "")
DIMS = ["methodology","results","author","duration","findings","summary",
        "formatting","inconsistency","plausibility"]
INTEGRITY = {"methodology","results","inconsistency","plausibility"}

GUNTING_SYS = (
 "You are a research-paper fraud auditor. Judge ONLY from the text shown. You have NO "
 "internet and must NOT assume outside knowledge about whether this paper was retracted. "
 "Score each of 9 integrity dimensions 0-100 (0=clean, 100=clear fraud/fabrication/"
 "paper-mill): methodology, results (data/stat integrity, figure-text consistency, too-"
 "clean/impossible numbers), author (affiliation reality, mill authorship signals in text), "
 "duration (timeline feasibility vs scope), findings (conclusions supported, overclaiming), "
 "summary (abstract matches body), formatting (tortured phrases, template artifacts, "
 "citation anomalies), inconsistency (internal contradictions, sample/number drift), "
 "plausibility (unrealistic/impossible claims). "
 'Output ONLY a JSON object with integer fields for all 9 dimensions, e.g. '
 '{"methodology":0,"results":0,"author":0,"duration":0,"findings":0,"summary":0,'
 '"formatting":0,"inconsistency":0,"plausibility":0}. No prose.')
VANILLA_SYS = ('You screen research papers. Judging ONLY from the text (no internet/outside '
 'knowledge), output ONLY {"fraud_score": <int 0-100>} (0=legit, 100=fraud/paper-mill).')

def gunting_overall(d):
    if any(v>=80 for v in d.values()): return max(d.values())
    num=sum(v*(1.5 if k in INTEGRITY else 1.0) for k,v in d.items())
    den=sum(1.5 if k in INTEGRITY else 1.0 for k in d)
    return round(num/den)

def call(system, user, think, max_tokens=4096, timeout=600):
    if not think:
        user = user + "\n\n/no_think"   # Qwen3 hard switch to disable reasoning
    body={"model":MODEL,"temperature":0,"stream":True,"max_tokens":max_tokens,
          "messages":[{"role":"system","content":system},{"role":"user","content":user}]}
    if not think:
        body["chat_template_kwargs"]={"enable_thinking":False}
    hdr={"Content-Type":"application/json"}
    if KEY: hdr["Authorization"]=f"Bearer {KEY}"
    req=urllib.request.Request(BASE+"/v1/chat/completions",data=json.dumps(body).encode(),headers=hdr)
    content=[]
    with urllib.request.urlopen(req,timeout=timeout) as r:
        for raw in r:
            line=raw.decode("utf-8","replace").strip()
            if not line.startswith("data:"): continue
            payload=line[5:].strip()
            if payload=="[DONE]": break
            try: delta=json.loads(payload)["choices"][0]["delta"]
            except Exception: continue
            if delta.get("content"): content.append(delta["content"])  # ignore reasoning_content
    return "".join(content)

def extract_json(s):
    # last {...} block
    matches=re.findall(r"\{[^{}]*\}", s, re.S)
    for m in reversed(matches):
        try: return json.loads(m)
        except Exception: pass
    # greedy fallback
    a,b=s.find("{"),s.rfind("}")
    if a>=0 and b>a:
        try: return json.loads(s[a:b+1])
        except Exception: pass
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",choices=["gunting","vanilla"],required=True)
    ap.add_argument("--blind",default="blind")
    ap.add_argument("--out",required=True)
    ap.add_argument("--think",action="store_true")
    args=ap.parse_args()
    sysmsg=GUNTING_SYS if args.config=="gunting" else VANILLA_SYS
    files=sorted(glob.glob(os.path.join(args.blind,"*.txt")))
    out=[]
    for fp in files:
        bid=os.path.splitext(os.path.basename(fp))[0]
        text=open(fp,encoding="utf-8").read()
        try:
            raw=call(sysmsg,"PAPER:\n"+text,args.think)
            obj=extract_json(raw)
            if obj is None: raise ValueError("no json in: "+raw[:80])
        except Exception as e:
            print(f"{bid} FAIL {str(e)[:70]}"); out.append({"id":bid,"score":0,"error":str(e)[:90]}); continue
        if args.config=="gunting":
            dims={}
            for d in DIMS:
                try: dims[d]=max(0,min(100,int(round(float(obj.get(d,0))))))
                except: dims[d]=0
            out.append({"id":bid,"score":gunting_overall(dims),"dimensions":dims})
        else:
            try: sc=max(0,min(100,int(round(float(obj.get("fraud_score",0))))))
            except: sc=0
            out.append({"id":bid,"score":sc})
        print(f"{bid} score {out[-1]['score']}")
    with open(args.out,"w") as f:
        for r in out: f.write(json.dumps(r)+"\n")
    print(f"\nwrote {args.out} ({len(out)} papers, model={MODEL}, think={args.think})")

if __name__=="__main__":
    main()
