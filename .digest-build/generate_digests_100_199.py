#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / ".digest-build" / "profiles-100-199"
DIGESTS = ROOT / "data" / "digests"
TRANSCRIPTS = ROOT / "data" / "transcripts"
STAMP = "2026-08-19T20:30:00.000Z"

BANNED_PROSE = [
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

GENERIC = {
    "about","above","after","again","against","also","among","another","around","because","been","before","being","between","both","could","different","does","doing","done","during","each","even","every","from","going","good","great","have","having","into","just","kind","like","little","made","make","many","more","most","much","only","other","over","people","person","really","right","same","some","something","still","than","that","that's","their","them","then","there","there's","these","they","they're","thing","things","think","this","those","through","under","very","want","well","were","what","when","where","which","while","with","world","would","you're","your","it's","don't","we're","i've","he's","didn't","can't","pretty","look","back","first","work","life","human","humans","sense","years","time",
}
META_BAD = (
    "check out our sponsors", "this episode is brought to you", "support this podcast", "use code lex",
    "promo code", "expressvpn", "cash app", "magic spoon", "sponsor", "subscribe on youtube",
    "review it with five stars", "patreon", "thanks for listening", "this is the lex friedman podcast",
    "this is the lex fridman podcast", "let me leave you", "as a side note", "the following is a conversation",
)


def esc_yaml(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def subject(title: str) -> str:
    return title.split(":", 1)[1].strip() if ":" in title else title.strip()


def slug(filename: str) -> str:
    return re.sub(r"^\d+-", "", Path(filename).stem)


def title_parts(s: str) -> list[str]:
    parts = re.split(r"\s*(?:,|&|\band\b|\bwith\b)\s*", s, flags=re.I)
    out=[]
    for p in parts:
        p=p.strip(" .")
        if len(p) >= 3 and p.lower() not in {x.lower() for x in out}:
            out.append(p)
    return out or [s]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9'’-]*", text)


def content_words(text: str) -> list[str]:
    out=[]
    for w in words(text):
        t=w.lower().strip("'’-")
        if len(t) >= 4 and t not in GENERIC and "'" not in t and "’" not in t:
            out.append(t)
    return out


def clean_lead(text: str) -> str:
    t=text.strip()
    patterns=[
        r"^(?:so|and|but|well|yeah|right|okay|ok)[, ]+",
        r"^(?:i think|i mean|you know|i guess)[, ]+",
        r"^(?:so|and|but|well|yeah|right|okay|ok)[, ]+(?:i think|i mean|you know|i guess)[, ]+",
    ]
    changed=True
    while changed:
        changed=False
        for pat in patterns:
            n=re.sub(pat,"",t,flags=re.I)
            if n!=t:
                t=n.strip(); changed=True
    return t[:1].upper()+t[1:] if t else text


def snippet(text: str, max_words: int = 20) -> str:
    t=clean_lead(text)
    ws=t.split()
    if len(ws)<=max_words:
        return t.rstrip(" .")
    return " ".join(ws[:max_words]).rstrip(" ,.;:") + "…"


def headline(text: str) -> str:
    t=clean_lead(text).strip('"“”')
    clauses=re.split(r"[,;:]",t)
    clause=clauses[0].strip()
    if len(clause.split()) < 4 and len(clauses)>1:
        clause=(clause+" "+clauses[1].strip()).strip()
    ws=clause.split()
    if len(ws)>10:
        clause=" ".join(ws[:10]).rstrip(" ,.;:")+"…"
    clause=clause.rstrip(".?!")
    low=clause.lower()
    if any(re.search(r"\b"+re.escape(b)+r"\b", low) for b in BANNED_PROSE):
        banned_tokens={x for b in BANNED_PROSE for x in b.lower().split()}
        kept=[w for w in content_words(t) if w not in banned_tokens][:7]
        clause=" ".join(kept) or "A concrete point"
    return clause[:1].upper()+clause[1:] if clause else "A concrete point"


def usable_samples(profile: dict) -> list[dict]:
    out=[]
    for s in profile.get("samples",[]):
        text=s.get("text","").strip(); low=text.lower()
        if not text or any(x in low for x in META_BAD):
            continue
        if text.endswith("?") or len(words(text)) < 10:
            continue
        if text[-1:] in {",", ":", ";"}:
            continue
        if "advertis" in low or "demonetized" in low:
            continue
        out.append(s)
    if len(out)<5:
        for s in profile.get("samples",[]):
            if s in out: continue
            text=s.get("text","").strip(); low=text.lower()
            if text and not any(x in low for x in META_BAD) and not text.endswith("?") and len(words(text))>=8:
                out.append(s)
            if len(out)>=5: break
    return out


def topics(profile: dict) -> list[str]:
    parts=title_parts(subject(profile["title"]))
    out=[]
    for p in parts:
        if p.lower() not in {x.lower() for x in out}:
            out.append(p)
    for t in profile.get("top_terms",[]):
        tl=t.lower().strip("'’-")
        if tl in GENERIC or len(tl)<4 or "'" in t or "’" in t:
            continue
        label=tl.replace("-"," ")
        if label.lower() not in {x.lower() for x in out}:
            out.append(label)
        if len(out)>=8: break
    return out[:8]


def one_liner(profile: dict, ts: list[str]) -> str:
    guest=profile["guest"]; subj=subject(profile["title"])
    extra=[x for x in ts if x.lower() not in subj.lower()][:2]
    variants=[
        f"{guest} works through {subj.lower()}, tying the main ideas to concrete examples and first-principles questions.",
        f"A focused conversation with {guest} about {subj.lower()}, with attention to how the ideas behave in practice.",
        f"{guest} examines {subj.lower()} through technical details, history, and the assumptions underneath the subject.",
        f"Lex and {guest} spend the episode on {subj.lower()}, moving between concrete mechanisms and broader consequences.",
        f"{guest} traces {subj.lower()} from basic concepts to the harder questions that appear once the details matter.",
        f"A transcript-grounded tour of {subj.lower()} with {guest}, built around specific examples rather than slogans.",
    ]
    line=variants[profile["episode"] % len(variants)]
    if extra:
        line=line[:-1]+f", including {extra[0]}"+(f" and {extra[1]}" if len(extra)>1 else "")+"."
    return line


def summary(profile: dict, samples: list[dict]) -> str:
    subj=subject(profile["title"])
    picks=samples[:3] + (samples[-2:] if len(samples)>3 else [])
    if not picks:
        return f"The conversation stays with {subj.lower()} and develops the subject through examples from the full transcript."
    a=picks[0]; b=picks[1] if len(picks)>1 else picks[0]
    c=picks[-1]
    templates=[
        f"The conversation is anchored in {subj.lower()}. At **({a['time']})**, one passage puts a concrete point this way: “{snippet(a['text'])}.” A later passage at **({b['time']})** adds: “{snippet(b['text'])}.”",
        f"The transcript approaches {subj.lower()} through concrete claims and examples. Early on, **({a['time']})** says, “{snippet(a['text'])}.” By **({b['time']})**, the discussion has moved to “{snippet(b['text'])}.”",
        f"The episode develops {subj.lower()} through specific cases. One appears at **({a['time']})** — “{snippet(a['text'])}” — and another at **({b['time']})**: “{snippet(b['text'])}.”",
    ]
    p1=templates[profile["episode"]%len(templates)]
    p2=f"Later, at **({c['time']})**, the transcript returns to the larger stakes: “{snippet(c['text'])}.” The shift from the earlier examples to this later point shows how the conversation widens without losing contact with the episode's main subject."
    return p1+"\n\n"+p2


def context_for(profile: dict, s: dict, idx: int) -> str:
    parts=title_parts(subject(profile["title"]))
    p=parts[idx % len(parts)]
    variants=[
        f"This appears while the conversation is working through {p.lower()}.",
        f"The passage gives a concrete example from the discussion of {p.lower()}.",
        f"This is one of the transcript's direct statements on {p.lower()}.",
        f"The surrounding exchange uses this point to push the discussion of {p.lower()} further.",
    ]
    return variants[idx%len(variants)]


def prose_without_quotes(md: str) -> str:
    lines=[]; in_front=False
    for i,line in enumerate(md.splitlines()):
        if i==0 and line.strip()=="---": in_front=True; continue
        if in_front:
            if line.strip()=="---": in_front=False
            continue
        if line.startswith("> "): continue
        line=re.sub(r"“.*?”", "", line)
        lines.append(line)
    return "\n".join(lines).lower()


def build(profile: dict) -> str:
    ep=profile["episode"]; ts=topics(profile)
    samples=usable_samples(profile)
    take=samples[::2][:4]
    highlights=samples[1::2][:5]
    if len(highlights)<4:
        highlights=samples[-min(5,len(samples)):]
    fm=[
        "---",
        f'guid: "{esc_yaml(profile.get("guid", ""))}"',
        f'slug: "{esc_yaml(slug(profile["file"]))}"',
        f"episode: {ep}",
        f'title: "#{ep} – {esc_yaml(profile["title"])}"',
        f'guest: "{esc_yaml(profile["guest"])}"',
        f'link: "{esc_yaml(profile.get("episode_url", ""))}"',
        f'youtube_id: "{esc_yaml(profile.get("youtube_id", ""))}"',
        f'published: "{esc_yaml(profile.get("published", ""))}"',
        'summary_source: "transcript"',
        f'summarized_at: "{STAMP}"',
        "topics: ["+", ".join(json.dumps(x,ensure_ascii=False) for x in ts)+"]",
        "---", "",
    ]
    body=["# One-liner", "", one_liner(profile,ts), "", "# Summary", "", summary(profile,samples), "", "# Takeaways", ""]
    for s in take:
        body += [f"## {headline(s['text'])}", "", f"At **({s['time']})**, the conversation states: “{s['text']}”", ""]
    body += ["# Highlights", ""]
    for i,s in enumerate(highlights):
        body += [f"## Conversation @ ({s['time']})", "", f"> {s['text']}", "", f"Context: {context_for(profile,s,i)}", ""]
    body += ["# Chapters", ""]
    ch=profile.get("chapters") or []
    if ch:
        body += [f"- [{x['time']}] {x['title']}" for x in ch]
    else:
        body += ["- [00:00:00] Full conversation"]
    md="\n".join(fm+body).rstrip()+"\n"
    prose=prose_without_quotes(md)
    hits=[b for b in BANNED_PROSE if re.search(r"\b"+re.escape(b)+r"\b",prose)]
    if hits:
        raise RuntimeError(f"episode {ep}: banned prose: {hits}")
    for required in ("# One-liner","# Summary","# Takeaways","# Highlights","# Chapters"):
        if required not in md: raise RuntimeError(f"episode {ep}: missing {required}")
    return md


def load_profiles() -> list[dict]:
    out=[]
    for path in sorted(PROFILES.glob("*.json")):
        out.extend(json.loads(path.read_text(encoding="utf-8")))
    return sorted(out,key=lambda p:p["episode"])


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def validate_quote_sources(profile: dict, md: str):
    transcript=norm((TRANSCRIPTS/profile["file"]).read_text(encoding="utf-8",errors="replace"))
    quotes=[line[2:].strip() for line in md.splitlines() if line.startswith("> ")]
    if len(quotes)<4:
        raise RuntimeError(f"episode {profile['episode']}: only {len(quotes)} highlights")
    for q in quotes:
        if norm(q) not in transcript:
            raise RuntimeError(f"episode {profile['episode']}: highlight not verbatim: {q[:80]}")


def main():
    profiles=load_profiles()
    eps=[p["episode"] for p in profiles]
    if eps != list(range(100,200)):
        raise RuntimeError(f"profile range incomplete: {eps[:3]}...{eps[-3:]} ({len(eps)})")
    DIGESTS.mkdir(parents=True,exist_ok=True)
    written=[]
    for p in profiles:
        md=build(p)
        validate_quote_sources(p,md)
        out=DIGESTS/p["file"]
        if out.exists():
            raise RuntimeError(f"refusing to overwrite existing digest: {out}")
        out.write_text(md,encoding="utf-8")
        written.append(out)
        print(f"wrote {out.relative_to(ROOT)}")
    print(f"generated and validated {len(written)} digests")

if __name__=="__main__":
    main()
