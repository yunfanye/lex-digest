#!/usr/bin/env python3
from __future__ import annotations

import collections
import html
import json
import math
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "data" / "transcripts"
MANIFEST = ROOT / "data" / "manifest.json"
OUT = ROOT / ".digest-build" / "profiles-100-199"

TS_PATTERNS = [
    re.compile(r"^\*\*\[(\d{1,2}:\d{2}:\d{2})\]\*\*\s*:?[ \t]*(.*)$"),
    re.compile(r"^\*\*\((\d{1,2}:\d{2}:\d{2})\)\*\*\s*:?[ \t]*(.*)$"),
    re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s*(.*)$"),
]
LABELED = re.compile(r"^\*\*(.+?)\*\*\s*\((\d{1,2}:\d{2}:\d{2})\):?\s*(.*)$")
CONT = re.compile(r"^\*\*\*\*\s*\((\d{1,2}:\d{2}:\d{2})\):?\s*(.*)$")
HEADING = re.compile(r"^#{2,4}\s+(.+?)\s*$")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘])")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.'’\-]*")

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves yeah yes okay well really actually basically kind sort mean right like thing things something anything everything probably maybe perhaps gonna wanna got get gets getting know knows knew say says said saying think thinks thought thinking one two three also much many lot lots little big good great make makes made making way time people person conversation question answer episode podcast lex fridman guest
""".split())
BAD = (
    "check out our sponsors", "this episode is brought to you", "support this podcast",
    "use code lex", "promo code", "expressvpn", "cash app", "magic spoon", "sponsor",
    "subscribe on youtube", "review it with five stars", "patreon", "thanks for listening",
    "the following is a conversation", "this is the artificial intelligence podcast",
)
BIO = {"professor","researcher","scientist","engineer","founder","author","historian","physicist","mathematician","philosopher","economist","journalist","athlete","champion","president","ceo","doctor","neuroscientist","programmer","director"}
STRONG = {"evidence","mechanism","reason","risk","tradeoff","failure","success","fundamental","future","history","power","freedom","truth","intelligence","consciousness","science","technology","war","peace","love","meaning","leadership","learning","evolution","democracy","security","incentive","uncertainty","responsibility","system","design","principle","memory","brain","physics","mathematics","algorithm","energy","life"}


def clean(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sec(ts: str) -> int:
    h,m,s = [int(x) for x in ts.split(":")]
    return h*3600+m*60+s


def normalize(ts: str) -> str:
    h,m,s = [int(x) for x in ts.split(":")]
    return f"{h:02d}:{m:02d}:{s:02d}"


def words(text: str) -> list[str]:
    return WORD.findall(text)


def toks(text: str) -> list[str]:
    out=[]
    for w in words(text):
        t=w.lower().strip(".'’-_")
        if t and t not in STOPWORDS and len(t)>=3 and not t.isdigit():
            out.append(t)
    return out


def parse(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines and lines[0].strip()=="---":
        for i in range(1,len(lines)):
            if lines[i].strip()=="---":
                lines=lines[i+1:]
                break
    segs=[]
    heading=None
    last_speaker=None
    labeled=0
    for raw in lines:
        line=raw.strip()
        if not line:
            continue
        mh=HEADING.match(line)
        if mh:
            heading=clean(mh.group(1))
            continue
        ml=LABELED.match(line)
        if ml:
            sp,ts,text=ml.groups(); last_speaker=clean(sp).strip("* ") or None
            labeled += bool(last_speaker)
            segs.append({"time":normalize(ts),"text":clean(text),"speaker":last_speaker,"heading":heading})
            continue
        mc=CONT.match(line)
        if mc:
            ts,text=mc.groups()
            segs.append({"time":normalize(ts),"text":clean(text),"speaker":last_speaker,"heading":heading})
            continue
        matched=None
        for pat in TS_PATTERNS:
            matched=pat.match(line)
            if matched: break
        if matched:
            ts,text=matched.groups(); last_speaker=None
            segs.append({"time":normalize(ts),"text":clean(text),"speaker":None,"heading":heading})
        elif segs:
            segs[-1]["text"]=clean(segs[-1]["text"]+" "+line)
    return segs, (labeled/max(len(segs),1) >= 0.20)


def sentence_candidates(segs, title, guest):
    title_tokens=set(toks(title+" "+guest))
    all_tokens=[]
    raw=[]
    for seg in segs:
        for sentence in SENTENCE_SPLIT.split(seg["text"]):
            sentence=clean(sentence)
            wc=len(words(sentence))
            low=sentence.lower()
            if wc < 12 or wc > 46 or sentence.endswith("?") or any(x in low for x in BAD):
                continue
            item={**seg,"text":sentence}
            raw.append(item)
            all_tokens.extend(toks(sentence))
    counts=collections.Counter(all_tokens)
    total=max(len(all_tokens),1)
    def score(item):
        tt=toks(item["text"])
        if not tt: return -99
        rarity=sum(min(4.0, math.log((total+50)/(counts[t]+1))) for t in tt)/len(tt)
        sc=rarity + 0.45*sum(t in title_tokens for t in tt) + 0.24*sum(t in STRONG for t in tt)
        wc=len(words(item["text"])); sc += max(0, 0.8-abs(wc-27)/28)
        if sec(item["time"])<180: sc-=1.0
        return sc
    return raw, score


def choose_samples(segs, title, guest, count=8):
    candidates, score=sentence_candidates(segs,title,guest)
    if not candidates: return []
    start=min(sec(x["time"]) for x in candidates); end=max(sec(x["time"]) for x in candidates)
    span=max(1,end-start)
    chosen=[]
    for b in range(count):
        lo=start+span*b/count; hi=start+span*(b+1)/count
        bucket=[x for x in candidates if lo <= sec(x["time"]) <= hi]
        if not bucket: continue
        best=max(bucket,key=score)
        chosen.append(best)
    # Fill any missing buckets with globally strong, time-distant passages.
    ranked=sorted(candidates,key=score,reverse=True)
    for item in ranked:
        if len(chosen)>=count: break
        if any(abs(sec(item["time"])-sec(x["time"]))<180 for x in chosen): continue
        chosen.append(item)
    chosen=sorted(chosen,key=lambda x:sec(x["time"]))[:count]
    return chosen


def top_terms(segs, title, guest, n=12):
    exclude=set(toks(title+" "+guest))
    c=collections.Counter(t for s in segs for t in toks(s["text"]) if t not in exclude)
    out=[]; stems=set()
    for t,_ in c.most_common(100):
        stem=t.rstrip("s")
        if stem in stems or len(t)<4: continue
        stems.add(stem); out.append(t)
        if len(out)>=n: break
    return out


def bio_candidate(segs, guest):
    surname=(guest.split()[-1].lower() if guest else "")
    candidates,_=sentence_candidates([s for s in segs if sec(s["time"])<900],guest,guest)
    best=None; best_score=-1
    for x in candidates:
        low=x["text"].lower(); ts=set(toks(x["text"]))
        sc=2*sum(b in ts for b in BIO) + (2 if surname and surname in low else 0)
        if sc>best_score: best_score=sc; best=x
    return best if best_score>=2 else None


def youtube_id(url):
    if not url: return ""
    p=urlparse(url)
    if "youtu.be" in p.netloc: return p.path.strip("/")
    return parse_qs(p.query).get("v",[""])[0]


def wordpress_guid(url):
    if not url: return ""
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 lex-digest-maintenance"})
        with urllib.request.urlopen(req,timeout=25) as r:
            page=r.read().decode("utf-8",errors="replace")
        for pat in (r"https://lexfridman\.com/\?p=(\d+)",r"postid-(\d+)"):
            m=re.search(pat,page,re.I)
            if m: return f"https://lexfridman.com/?p={m.group(1)}"
    except Exception as e:
        print(f"GUID fetch failed for {url}: {e}")
    return ""


def chapters(segs):
    out=[]; seen=set()
    for s in segs:
        h=s.get("heading")
        if h and h not in seen:
            seen.add(h); out.append({"time":s["time"],"title":h})
    return out


def main():
    rows=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows={int(r["episode"]):r for r in rows if 100<=int(r["episode"])<=199}
    OUT.mkdir(parents=True,exist_ok=True)
    profiles=[]
    for ep in range(100,200):
        row=rows[ep]; path=TRANSCRIPTS/row["file"]
        segs,reliable=parse(path)
        samples=choose_samples(segs,row.get("title", ""),row.get("guest", ""),8)
        bio=bio_candidate(segs,row.get("guest", ""))
        guid=wordpress_guid(row.get("episode_url", ""))
        profile={
            "episode":ep,"file":row["file"],"title":row.get("title", ""),"guest":row.get("guest", ""),
            "published":row.get("published", ""),"episode_url":row.get("episode_url", ""),
            "youtube_url":row.get("youtube_url", ""),"youtube_id":youtube_id(row.get("youtube_url", "")),
            "source":row.get("source", ""),"quality":row.get("quality", ""),"guid":guid,
            "reliable_speaker_labels":reliable,"duration":segs[-1]["time"] if segs else "",
            "top_terms":top_terms(segs,row.get("title", ""),row.get("guest", ""),12),
            "bio":({"time":bio["time"],"text":bio["text"],"speaker":bio.get("speaker")} if bio else None),
            "samples":[{"time":x["time"],"text":x["text"],"speaker":x.get("speaker"),"heading":x.get("heading")} for x in samples],
            "chapters":chapters(segs),
        }
        profiles.append(profile)
        print(f"profile {ep}: {len(segs)} segments, {len(samples)} samples, guid={guid or 'missing'}")
        if ep%10==9: time.sleep(0.4)
    for start in range(100,200,5):
        batch=[p for p in profiles if start<=p["episode"]<start+5]
        (OUT/f"{start}-{start+4}.json").write_text(json.dumps(batch,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
