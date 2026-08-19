#!/usr/bin/env python3
"""Fetch eps 326-384 from lawwu/transcripts Whisper archive -> uniform markdown."""
import json, re, html, time, os, sys, urllib.request

WORK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WORK, "..", "transcripts")
META = json.load(open(os.path.join(WORK, "meta.json")))
YTMAP = json.load(open(os.path.join(WORK, "ytmap.json")))

def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))

def ts_to_sec(ts):
    p = [float(x) for x in ts.split(":")]
    return p[0]*3600 + p[1]*60 + p[2] if len(p) == 3 else p[0]*60 + p[1]

def hms(s):
    s = int(s); return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

def slug_of(m):
    u = m.get("episode_url") or ""
    s = u.rstrip("/").split("/")[-1]
    return s or re.sub(r"[^a-z0-9]+", "-", m["guest"].lower()).strip("-")

def yesc(s): return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

SEG_RE = re.compile(r'<div class="c"><span class="s"><a [^>]*>([\d:.]+)</a></span> \| <span class="t">([\s\S]*?)</span></div>')
CHAP_RE = re.compile(r'<a href="https://www\.youtube\.com/watch\?v=[\w-]+&t=(\d+)">[\d:]+</a> ([^<]+)<br>')

def main():
    nums = [int(a) for a in sys.argv[1:]] or list(range(326, 385))
    ok, fail = [], []
    for n in nums:
        m = META[str(n)]
        vid = YTMAP[str(n)]
        url = f"https://raw.githubusercontent.com/lawwu/transcripts/main/docs/{vid}.html"
        try:
            page = fetch(url)
            tm = re.search(r"<title>(.*?)</title>", page, re.S)
            title = html.unescape(tm.group(1)) if tm else ""
            if f"#{n}" not in title:
                raise RuntimeError(f"episode number #{n} not in page title: {title[:90]}")
            chapters = [(int(s), html.unescape(t).strip()) for s, t in CHAP_RE.findall(page)]
            segs = [(ts_to_sec(ts), html.unescape(t).strip()) for ts, t in SEG_RE.findall(page)]
            segs = [s for s in segs if s[1]]
            if len(segs) < 50:
                raise RuntimeError(f"only {len(segs)} segments")
            # merge into 60s blocks, breaking at chapter boundaries
            bounds = sorted(set(c[0] for c in chapters))
            chap_at = {c[0]: c[1] for c in chapters}
            lines, cur_start, cur_texts = [], None, []
            next_b = 0
            def flush():
                if cur_texts:
                    lines.append(f"**[{hms(cur_start)}]** {' '.join(cur_texts)}\n")
            for st, txt in segs:
                boundary = None
                while next_b < len(bounds) and st >= bounds[next_b]:
                    boundary = bounds[next_b]; next_b += 1
                if boundary is not None:
                    flush(); cur_start, cur_texts = st, []
                    lines.append(f"\n## {chap_at[boundary]}\n")
                elif cur_start is not None and st - cur_start >= 60:
                    flush(); cur_start, cur_texts = st, []
                if cur_start is None: cur_start = st
                cur_texts.append(txt)
            flush()
            body = "\n".join(lines)
            head = ["---", f"episode: {n}",
                    f"title: {yesc('#' + str(n) + ' – ' + m['title'])}",
                    f"guest: {yesc(m['guest'])}",
                    f"published: {m['published'] or 'unknown'}",
                    "source: lawwu/transcripts Whisper archive (ggml-large-v2)",
                    f"source_url: https://lawwu.github.io/transcripts/{vid}.html",
                    "quality: machine (Whisper, no speaker labels)",
                    "---", "", ""]
            fn = f"{n:03d}-{slug_of(m)}.md"
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                f.write("\n".join(head) + body)
            ok.append(n)
            print(f"OK  {n} {fn} segs={len(segs)} chaps={len(chapters)} chars={len(body)}", flush=True)
        except Exception as e:
            fail.append(n)
            print(f"FAIL {n} {vid} :: {e}", flush=True)
        time.sleep(0.5)
    print(f"\nDONE ok={len(ok)} fail={len(fail)} {fail}")

if __name__ == "__main__":
    main()
