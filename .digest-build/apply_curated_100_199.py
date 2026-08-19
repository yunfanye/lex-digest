#!/usr/bin/env python3
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGESTS = ROOT / "data" / "digests"
TRANSCRIPTS = ROOT / "data" / "transcripts"
BUILD = ROOT / ".digest-build"

BANNED = [
    "delve", "foster", "leverage", "utilize", "facilitate", "empower", "streamline",
    "robust", "cutting-edge", "paradigm shift", "game changer", "this is huge",
    "this changes everything", "tapestry", "realm", "beacon", "multifaceted",
    "meticulous", "intricate", "paramount", "transformative", "elevate", "embark",
    "supercharge", "harness", "it's worth noting", "it is worth noting",
    "it's important to note", "it is important to note", "at the end of the day",
    "when it comes to", "at its core", "in today's world", "in the age of",
    "in the world of", "the reality is", "the truth is", "in terms of",
    "with regard to", "in order to", "going forward", "in this article", "let's dive in",
]
STOP = set("""
a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves conversation episode discussion explains argues treats asks uses shows describes returns connects presents people person human humans idea ideas work working make makes made making good great different first second later also still one two three much many really like thing things way time years
""".split())
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’-]*")
TS = re.compile(r"\d{2}:\d{2}:\d{2}")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def secs(ts: str) -> int:
    h,m,s = map(int, ts.split(":")); return h*3600+m*60+s


def tokens(s: str) -> list[str]:
    out=[]
    for w in WORD.findall(s.lower()):
        t=w.strip("'’-")
        if len(t)>=4 and t not in STOP and not t.isdigit(): out.append(t)
    return out


def load_curated() -> dict[int, dict]:
    merged={}
    for name in ("curated-100-149.json", "curated-150-199.json"):
        data=json.loads((BUILD/name).read_text(encoding="utf-8"))
        merged.update({int(k):v for k,v in data.items()})
    if sorted(merged) != list(range(100,200)):
        raise RuntimeError(f"curated range incomplete: {len(merged)} entries")
    return merged


def digest_path(ep: int) -> Path:
    matches=list(DIGESTS.glob(f"{ep}-*.md"))
    if len(matches)!=1: raise RuntimeError(f"episode {ep}: expected one digest, found {matches}")
    return matches[0]


def transcript_path(ep: int) -> Path:
    matches=list(TRANSCRIPTS.glob(f"{ep}-*.md"))
    if len(matches)!=1: raise RuntimeError(f"episode {ep}: expected one transcript, found {matches}")
    return matches[0]


def frontmatter_and_chapters(text: str) -> tuple[str,str]:
    if not text.startswith("---\n"):
        raise RuntimeError("missing frontmatter")
    end=text.find("\n---\n",4)
    if end<0: raise RuntimeError("unterminated frontmatter")
    fm=text[:end+5]
    idx=text.find("# Chapters")
    chapters=text[idx:] if idx>=0 else "# Chapters\n\n- [00:00:00] Full conversation\n"
    return fm, chapters.rstrip()+"\n"


def extract_quotes(text: str) -> list[dict]:
    found=[]
    for m in re.finditer(r"At \*\*\((\d{2}:\d{2}:\d{2})\)\*\*, the conversation states: “(.*?)”", text, re.S):
        found.append({"time":m.group(1),"text":norm(m.group(2))})
    for m in re.finditer(r"## (?:Conversation|[^\n]+?) @ \((\d{2}:\d{2}:\d{2})\)\s*\n\s*> (.*?)(?=\n\s*Context:|\n## |\n# Chapters|\Z)", text, re.S):
        found.append({"time":m.group(1),"text":norm(m.group(2))})
    unique=[]; seen=set()
    for q in found:
        key=(q["time"],q["text"])
        if key not in seen:
            seen.add(key); unique.append(q)
    return unique


def quote_score(q: dict, curated: dict) -> float:
    text=q["text"]; low=text.lower(); ws=WORD.findall(text)
    sc=0.0
    n=len(ws)
    sc += max(0, 4.0-abs(n-24)/6)
    fillers=sum(low.count(x) for x in (" um "," uh "," hmm"," you know"," i mean"," kind of"," sort of"))
    sc -= fillers*1.5
    if re.match(r"^(hmm|uh|um|yeah|okay|so|and|but)\b", low): sc-=1.0
    if re.search(r"\b(it's it's|the the|i i|and and|to to|that that)\b", low): sc-=2.0
    if text[-1:] in {",",":",";"}: sc-=3.0
    theme=set(tokens(curated["one"]+" "+" ".join(h+" "+b for h,b in curated["takes"])))
    sc += min(4, len(theme.intersection(tokens(text))))*0.7
    return sc


def choose_quotes(quotes: list[dict], curated: dict, count: int=5) -> list[dict]:
    ranked=sorted(quotes,key=lambda q:quote_score(q,curated),reverse=True)
    chosen=[]
    for q in ranked:
        if any(abs(secs(q["time"])-secs(x["time"]))<240 for x in chosen): continue
        chosen.append(q)
        if len(chosen)>=count: break
    if len(chosen)<4:
        for q in ranked:
            if q not in chosen: chosen.append(q)
            if len(chosen)>=4: break
    return sorted(chosen,key=lambda q:secs(q["time"]))


def match_takeaway(q: dict, takes: list[list[str]]) -> str:
    qt=set(tokens(q["text"]))
    best=None; score=-1
    for heading,body in takes:
        st=set(tokens(heading+" "+body)); s=len(qt & st)
        if s>score: score=s; best=heading
    return best or takes[0][0]


def topics(curated: dict) -> list[str]:
    text=curated["one"]+" "+" ".join(h+" "+b for h,b in curated["takes"])
    c=collections.Counter(tokens(text))
    guestish=set()
    # Prefer repeated, content-heavy terms; dedupe simple singular/plural variants.
    out=[]; stems=set()
    for t,n in c.most_common(50):
        stem=t.rstrip("s")
        if stem in stems or t in guestish: continue
        if n<2 and len(out)>=5: continue
        stems.add(stem); out.append(t.replace("-"," "))
        if len(out)>=8: break
    # Guarantee a useful list even for sparse entries.
    if len(out)<6:
        for h,_ in curated["takes"]:
            for t in tokens(h):
                stem=t.rstrip("s")
                if stem not in stems:
                    stems.add(stem); out.append(t)
                if len(out)>=6: break
            if len(out)>=6: break
    return out[:8]


def update_frontmatter(fm: str, curated: dict) -> str:
    arr=", ".join(json.dumps(x,ensure_ascii=False) for x in topics(curated))
    fm=re.sub(r"(?m)^topics:.*$", f"topics: [{arr}]", fm)
    return fm


def scan_style(ep: int, curated: dict):
    prose=curated["one"]+"\n"+"\n".join(h+"\n"+b for h,b in curated["takes"])
    low=prose.lower()
    hits=[b for b in BANNED if re.search(r"\b"+re.escape(b)+r"\b",low)]
    if hits: raise RuntimeError(f"episode {ep}: banned curated prose {hits}")
    if re.search(r"\bnot\s+[^.!?]{1,70}\bbut\b", low):
        raise RuntimeError(f"episode {ep}: 'not X but Y' construction in curated prose")


def build(ep: int, curated: dict, old: str) -> str:
    scan_style(ep,curated)
    fm,chapters=frontmatter_and_chapters(old)
    fm=update_frontmatter(fm,curated)
    quotes=choose_quotes(extract_quotes(old),curated)
    if len(quotes)<4: raise RuntimeError(f"episode {ep}: insufficient exact highlights")
    bodies=[b for _,b in curated["takes"]]
    summary1=" ".join(bodies[:2])
    summary2=" ".join(bodies[2:])
    parts=[fm.rstrip(),"","# One-liner","",curated["one"],"","# Summary","",summary1,"",summary2,"","# Takeaways",""]
    for heading,body in curated["takes"]:
        parts += [f"## {heading}","",body,""]
    parts += ["# Highlights",""]
    for q in quotes:
        heading=match_takeaway(q,curated)
        parts += [f"## Conversation @ ({q['time']})","",f"> {q['text']}","",f"Context: On {heading.lower()}.",""]
    parts += [chapters.rstrip(),""]
    return "\n".join(parts)


def validate(ep: int, md: str):
    for h in ("# One-liner","# Summary","# Takeaways","# Highlights","# Chapters"):
        if md.count(h)!=1: raise RuntimeError(f"episode {ep}: bad heading count for {h}")
    transcript=norm(transcript_path(ep).read_text(encoding="utf-8",errors="replace"))
    quotes=[norm(x) for x in re.findall(r"(?m)^> (.+)$",md)]
    if len(quotes)<4: raise RuntimeError(f"episode {ep}: fewer than four highlights")
    for q in quotes:
        if q not in transcript: raise RuntimeError(f"episode {ep}: highlight not verbatim: {q[:100]}")


def main():
    curated=load_curated()
    for ep in range(100,200):
        path=digest_path(ep)
        old=path.read_text(encoding="utf-8")
        new=build(ep,curated[ep],old)
        validate(ep,new)
        path.write_text(new,encoding="utf-8")
        print(f"rewrote {path.relative_to(ROOT)}")
    print("curated and validated 100 digests")

if __name__=="__main__":
    main()
