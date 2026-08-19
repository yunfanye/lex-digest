#!/usr/bin/env python3
"""Fetch official lexfridman.com transcripts and write uniform markdown."""
import json, re, html, time, sys, os, urllib.request

WORK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WORK, "..", "transcripts")
META = json.load(open(os.path.join(WORK, "meta.json")))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

TOKEN_RE = re.compile(
    r'<h2 id="chapter\d+_[^"]*">\s*<span id="[^"]*">([^<]*)</span>\s*</h2>'
    r'|<div class="ts-segment">\s*<span class="ts-name">([\s\S]*?)</span>\s*'
    r'<span class="ts-timestamp">([\s\S]*?)</span>\s*<span class="ts-text">([\s\S]*?)</span>')

def strip_tags(s): return re.sub(r"<[^>]+>", "", s)
def clean(s): return html.unescape(strip_tags(s)).strip()

def slug_of(m):
    u = m.get("episode_url") or m.get("transcript_url") or ""
    s = u.rstrip("/").split("/")[-1].replace("-transcript", "")
    return s or re.sub(r"[^a-z0-9]+", "-", m["guest"].lower()).strip("-")

def yaml_escape(s): return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def write_md(num, m, source, source_url, quality, body):
    fn = f"{num:03d}-{slug_of(m)}.md"
    head = [
        "---",
        f"episode: {num}",
        f"title: {yaml_escape('#' + str(num) + ' – ' + m['title'])}",
        f"guest: {yaml_escape(m['guest'])}",
        f"published: {m['published'] or 'unknown'}",
        f"source: {source}",
        f"source_url: {source_url}",
        f"quality: {quality}",
        "---", "",
    ]
    with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
        f.write("\n".join(head) + body)
    return fn

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))

def parse_official(page):
    chapters, segments = [], []
    cur = None
    for mt in TOKEN_RE.finditer(page):
        if mt.group(1) is not None:
            cur = clean(mt.group(1))
            continue
        speaker = clean(mt.group(2))
        ts = clean(mt.group(3)).strip("()")
        text = clean(mt.group(4))
        if not text: continue
        segments.append((cur, speaker, ts, text))
    return segments

def render(segments):
    lines, last_ch = [], object()
    for ch, speaker, ts, text in segments:
        if ch != last_ch and ch:
            lines.append(f"\n## {ch}\n")
            last_ch = ch
        lines.append(f"**{speaker}** ({ts}): {text}\n")
    return "\n".join(lines)

def main():
    nums = [int(a) for a in sys.argv[1:]] or [n for n in range(385, 501) if n != 478]
    ok, fail = [], []
    for n in nums:
        m = META[str(n)]
        url = m["transcript_url"].rstrip("/") + "/"
        try:
            page = fetch(url)
            segs = parse_official(page)
            if len(segs) < 10:
                raise RuntimeError(f"only {len(segs)} segments parsed")
            body = render(segs)
            fn = write_md(n, m, "lexfridman.com official transcript", url, "human", body)
            ok.append(n)
            print(f"OK  {n} {fn} segs={len(segs)} chars={len(body)}", flush=True)
        except Exception as e:
            fail.append(n)
            print(f"FAIL {n} {url} :: {e}", flush=True)
        time.sleep(1.2)
    print(f"\nDONE ok={len(ok)} fail={len(fail)} {fail}")

if __name__ == "__main__":
    main()
