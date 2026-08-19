#!/usr/bin/env python3
"""Fetch hole episodes from PodScripts -> uniform markdown."""
import json, re, html, time, os, sys, urllib.request

WORK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WORK, "..", "transcripts")
META = json.load(open(os.path.join(WORK, "meta.json")))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

def slugify(t):
    s = t.lower().replace("&", "and").replace("\u2019", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def slug_of(m):
    u = m.get("episode_url") or ""
    s = u.rstrip("/").split("/")[-1]
    return s or slugify(m["guest"])

def yesc(s): return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

TOKEN_RE = re.compile(
    r'<span class="pod_timestamp_indicator">Starting point is ([\d:]+)</span>'
    r'|<span id="sentenceid_\d+" class="pod_text[^"]*">([\s\S]*?)</span>')

def clean(s):
    s = re.sub(r"<!--.*?-->", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))

def main():
    nums = [int(a) for a in sys.argv[1:]] or [268, 282, 283, 287, 291, 478]
    ok, fail = [], []
    for n in nums:
        m = META[str(n)]
        url = f"https://podscripts.co/podcasts/lex-fridman-podcast/{n}-{slugify(m['title'])}"
        try:
            page = fetch(url)
            blocks, cur_ts, cur_texts = [], None, []
            for mt in TOKEN_RE.finditer(page):
                if mt.group(1) is not None:
                    if cur_texts:
                        blocks.append((cur_ts, " ".join(cur_texts)))
                    cur_ts, cur_texts = mt.group(1), []
                else:
                    t = clean(mt.group(2))
                    if t: cur_texts.append(t)
            if cur_texts: blocks.append((cur_ts, " ".join(cur_texts)))
            if len(blocks) < 20:
                raise RuntimeError(f"only {len(blocks)} blocks parsed")
            body = "\n\n".join(f"**[{ts or '00:00:00'}]** {t}" for ts, t in blocks)
            head = ["---", f"episode: {n}",
                    f"title: {yesc('#' + str(n) + ' – ' + m['title'])}",
                    f"guest: {yesc(m['guest'])}",
                    f"published: {m['published'] or 'unknown'}",
                    "source: PodScripts.co automated transcript",
                    f"source_url: {url}",
                    "quality: machine (speech-to-text, no speaker labels)",
                    "---", "", ""]
            fn = f"{n:03d}-{slug_of(m)}.md"
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                f.write("\n".join(head) + body + "\n")
            ok.append(n)
            print(f"OK  {n} {fn} blocks={len(blocks)} chars={len(body)}", flush=True)
        except Exception as e:
            fail.append(n)
            print(f"FAIL {n} {url} :: {e}", flush=True)
        time.sleep(2)
    print(f"\nDONE ok={len(ok)} fail={len(fail)} {fail}")

if __name__ == "__main__":
    main()
