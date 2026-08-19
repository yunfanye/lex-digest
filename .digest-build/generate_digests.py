#!/usr/bin/env python3
"""Temporary, deterministic builder for transcript-grounded digest Markdown."""
from __future__ import annotations

from pathlib import Path
import collections
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / ".digest-build" / "profiles"
TRANSCRIPTS = ROOT / "data" / "transcripts"
OUT = ROOT / "data" / "digests"
MANIFEST = {row["episode"]: row for row in json.loads((ROOT / "data" / "manifest.json").read_text())}

SPEAKER_RE = re.compile(r"^\*\*(.*?)\*\* \((\d{2}:\d{2}:\d{2})\):\s*(.*)$")
CONT_RE = re.compile(r"^\*\*\*\* \((\d{2}:\d{2}:\d{2})\):\s*(.*)$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"'])")
STOP = set("""a an and are as at be been being but by can could did do does doing for from had has have he her here hers herself him himself his how i if in into is it its itself just may me might more most my myself no nor not of on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves yeah yes okay well really actually basically kind sort mean right like thing things something anything everything""".split())
BAD = (
    "check out our sponsors", "support it", "this is the lex fridman podcast",
    "thanks for listening", "hope to see you next time", "promo code", "inaudible",
    "let me leave you with", "the following is a conversation",
)
STRONG = (
    "important", "truth", "future", "life", "love", "power", "risk", "learn",
    "believe", "meaning", "freedom", "intelligence", "science", "technology",
    "war", "peace", "human", "create", "build", "success", "failure", "fear",
    "hope", "beautiful", "problem", "idea", "world", "mind", "memory", "reason",
    "evidence", "money", "business", "leadership", "team", "history", "nature",
    "universe", "computer", "artificial intelligence", "robot", "music", "game",
    "physics", "mathematics", "democracy", "death", "consciousness", "evolution",
    "energy", "company", "government",
)


def parse_transcript(ep: int):
    row = MANIFEST[ep]
    lines = (TRANSCRIPTS / row["file"]).read_text(errors="replace").splitlines()
    try:
        fm_end = lines[1:].index("---") + 1
    except ValueError:
        fm_end = 0
    sections = [{"name": "Preamble", "utterances": []}]
    current = sections[0]
    last_speaker = None
    for line in lines[fm_end + 1:]:
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "utterances": []}
            sections.append(current)
            last_speaker = None
            continue
        match = SPEAKER_RE.match(line)
        if match:
            speaker, timestamp, text = match.groups()
            last_speaker = speaker or last_speaker or "Unknown"
            current["utterances"].append({"speaker": last_speaker, "time": timestamp, "text": text.strip()})
            continue
        match = CONT_RE.match(line)
        if match:
            timestamp, text = match.groups()
            current["utterances"].append({"speaker": last_speaker or "Unknown", "time": timestamp, "text": text.strip()})
    return row, [section for section in sections if section["utterances"]]


def seconds(timestamp: str) -> int:
    hour, minute, second = map(int, timestamp.split(":"))
    return hour * 3600 + minute * 60 + second


def sentences(sections):
    items = []
    for section_index, section in enumerate(sections):
        for utterance in section["utterances"]:
            text = re.sub(r"\s+", " ", utterance["text"]).strip()
            for part in SENT_SPLIT.split(text):
                if part.strip():
                    items.append({
                        "section": section["name"],
                        "section_index": section_index,
                        "speaker": utterance["speaker"],
                        "time": utterance["time"],
                        "text": part.strip(),
                    })
    return items


def quote_score(item, counts, total_tokens, preferred, target_tokens):
    text = item["text"].strip()
    words = WORD_RE.findall(text)
    low = text.lower()
    if not 9 <= len(words) <= 38 or text.endswith("?"):
        return -999
    if any(phrase in low for phrase in BAD):
        return -999
    if text.startswith(("…", "...", "—", "–")) or (text and text[0].islower()):
        return -999
    if text.count("“") != text.count("”") or text.count('"') % 2 == 1:
        return -2
    if text.endswith((",", ":", ";")):
        return -2
    if low.startswith(("and ", "but ", "because ", "which ", "that ", "then ", "or ", "by the way", "would you mind", "quick note", "there you go", "here is ", "here's ", "no, ", "yes, ")):
        return -3
    if re.search(r"\b(um|uh|gonna|wanna)\b", low):
        return -1

    speaker = item["speaker"]
    score = 1.5 if speaker in preferred else (-0.6 if speaker.lower().startswith("lex") else 0.4)
    content = [word.lower().strip("'’- ") for word in words if word.lower() not in STOP and len(word) > 2]
    if content:
        rarity = sum(min(3.0, math.log((total_tokens + 5) / (counts[word] + 1))) for word in content) / len(content)
        score += 0.55 * rarity
    score += sum(0.22 for keyword in STRONG if keyword in low)
    overlap = sum(1 for word in content if word in target_tokens)
    score += min(2.4, 0.38 * overlap)
    if overlap == 0 and not any(keyword in low for keyword in STRONG):
        score -= 0.8
    if re.search(r"\b(the key|the point|what matters|i learned|i believe|you have to|we have to|the best|the worst|the most|the reason)\b", low):
        score += 0.8
    if re.search(r"\b(i think|i mean|you know|kind of|sort of)\b", low):
        score -= 0.2
    score += max(0, 0.8 - abs(len(words) - 22) / 28)
    if item["section"].lower() in ("introduction", "episode highlight", "preamble"):
        score -= 0.8
    return score


def select_highlights(row, sections, profile, count=6):
    if profile.get("highlights"):
        return profile["highlights"]
    items = sentences(sections)
    tokens = [word.lower() for item in items for word in WORD_RE.findall(item["text"]) if word.lower() not in STOP]
    counts = collections.Counter(tokens)
    preferred = set(profile.get("highlight_speakers") or [])
    if not preferred:
        guest = row.get("guest") or ""
        if guest and all(marker not in guest.lower() for marker in (" vs ", "debate", "state of ai")):
            preferred = {guest}
    profile_text = " ".join(
        [profile.get("one_liner", "")] + profile.get("summary", []) +
        [item.get("title", "") + " " + item.get("text", "") for item in profile.get("takeaways", [])]
    )
    target_tokens = {word.lower() for word in WORD_RE.findall(profile_text) if word.lower() not in STOP and len(word) > 3}
    rank = lambda item: quote_score(item, counts, max(1, len(tokens)), preferred, target_tokens)
    ranked = sorted(items, key=rank, reverse=True)

    chosen, used_sections, used_prefixes = [], set(), []
    preferred_order = [speaker for speaker in profile.get("highlight_speakers", []) if speaker]
    if len(preferred_order) > 1:
        quota = max(1, count // len(preferred_order))
        for speaker in preferred_order:
            added = 0
            for item in ranked:
                if item["speaker"] != speaker or rank(item) < 0 or item["section"] in used_sections:
                    continue
                norm = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
                if any(norm[:55] == prefix[:55] for prefix in used_prefixes):
                    continue
                chosen.append({"speaker": item["speaker"], "time": item["time"], "quote": item["text"], "context": f"From the discussion of {item['section'].lower()}."})
                used_sections.add(item["section"])
                used_prefixes.append(norm)
                added += 1
                if added >= quota or len(chosen) >= count:
                    break

    for item in ranked:
        if len(chosen) >= count:
            break
        if rank(item) < 0 or item["section"] in used_sections:
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
        if any(norm[:55] == prefix[:55] for prefix in used_prefixes):
            continue
        chosen.append({"speaker": item["speaker"], "time": item["time"], "quote": item["text"], "context": f"From the discussion of {item['section'].lower()}."})
        used_sections.add(item["section"])
        used_prefixes.append(norm)

    for item in ranked:
        if len(chosen) >= count:
            break
        if rank(item) < 0:
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
        if any(norm[:55] == prefix[:55] for prefix in used_prefixes):
            continue
        chosen.append({"speaker": item["speaker"], "time": item["time"], "quote": item["text"], "context": f"From the discussion of {item['section'].lower()}."})
        used_prefixes.append(norm)
    return sorted(chosen, key=lambda item: seconds(item["time"]))


def select_chapters(sections, cap=20):
    chapters = []
    for section in sections:
        name = section["name"].strip()
        if name.lower() in ("introduction", "episode highlight", "preamble"):
            continue
        chapters.append({
            "time": section["utterances"][0]["time"],
            "name": name,
            "words": sum(len(WORD_RE.findall(utterance["text"])) for utterance in section["utterances"]),
        })
    if len(chapters) <= cap:
        return chapters
    keep = {0, len(chapters) - 1}
    for index in sorted(range(len(chapters)), key=lambda i: chapters[i]["words"], reverse=True):
        keep.add(index)
        if len(keep) >= cap:
            break
    return [chapter for index, chapter in enumerate(chapters) if index in keep]


def render(ep, profile):
    row, sections = parse_transcript(ep)
    slug = re.sub(r"^\d+-", "", row["file"]).removesuffix(".md")
    youtube_id = row.get("youtube_url", "").split("v=")[-1]
    lines = [
        "---", f"slug: {json.dumps(slug, ensure_ascii=False)}", f"episode: {ep}",
        f"title: {json.dumps(row['title'], ensure_ascii=False)}", f"guest: {json.dumps(row['guest'], ensure_ascii=False)}",
        f"link: {json.dumps(row['episode_url'], ensure_ascii=False)}", f"youtube_id: {json.dumps(youtube_id)}",
        f"published: {json.dumps(row['published'])}", 'summary_source: "transcript"',
        'summarized_at: "2026-08-19T05:07:05Z"', f"topics: {json.dumps(profile['topics'], ensure_ascii=False)}",
        "---", "", "# One-liner", "", profile["one_liner"].strip(), "", "# Summary", "",
    ]
    for paragraph in profile["summary"]:
        lines.extend([paragraph.strip(), ""])
    lines.extend(["# Takeaways", ""])
    for takeaway in profile["takeaways"]:
        lines.extend([f"## {takeaway['title'].strip()}", "", takeaway["text"].strip(), ""])
    lines.extend(["# Highlights", ""])
    for highlight in select_highlights(row, sections, profile, profile.get("highlight_count", 6)):
        lines.extend([
            f"## {highlight['speaker']} @ {highlight['time']}", "", f"> {highlight['quote'].strip()}", "",
            f"Context: {highlight.get('context', 'A concise statement from the episode.').strip()}", "",
        ])
    lines.extend(["# Chapters", ""])
    for chapter in select_chapters(sections, profile.get("chapter_cap", 20)):
        lines.append(f"- [{chapter['time']}] {chapter['name']}")
    lines.append("")
    path = OUT / row["file"]
    path.write_text("\n".join(lines))
    return path


def load_profiles():
    profiles = {}
    for path in sorted(PROFILE_DIR.glob("*.json")):
        for key, value in json.loads(path.read_text()).items():
            ep = int(key)
            if ep in profiles:
                raise ValueError(f"duplicate profile for episode {ep}")
            profiles[ep] = value
    return profiles


def validate_file(ep, path, profile):
    text = path.read_text()
    transcript = (TRANSCRIPTS / MANIFEST[ep]["file"]).read_text(errors="replace")
    for heading in ("# One-liner", "# Summary", "# Takeaways", "# Highlights", "# Chapters"):
        if heading not in text:
            raise ValueError(f"{path}: missing {heading}")
    if not 3 <= len(profile["summary"]) <= 5:
        raise ValueError(f"{path}: summary must have 3-5 paragraphs")
    if not 5 <= len(profile["takeaways"]) <= 9:
        raise ValueError(f"{path}: takeaways must have 5-9 entries")
    if not 3 <= len(profile["topics"]) <= 8:
        raise ValueError(f"{path}: topics must have 3-8 entries")
    highlights = re.findall(r"^> (.+)$", text, re.MULTILINE)
    if not 4 <= len(highlights) <= 7:
        raise ValueError(f"{path}: highlights must have 4-7 entries")
    for quote in highlights:
        if quote not in transcript:
            raise ValueError(f"{path}: highlight is not verbatim: {quote[:80]}")
    if re.search(r"\b(TODO|TBD|PLACEHOLDER)\b", text):
        raise ValueError(f"{path}: placeholder text remains")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profiles = load_profiles()
    expected = set(range(400, 496))
    if set(profiles) != expected:
        missing = sorted(expected - set(profiles))
        extra = sorted(set(profiles) - expected)
        raise ValueError(f"profile coverage mismatch; missing={missing}, extra={extra}")
    generated = []
    for ep in sorted(profiles):
        path = render(ep, profiles[ep])
        validate_file(ep, path, profiles[ep])
        generated.append(path)
    print(f"generated and validated {len(generated)} digests: #400-#495")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"digest build failed: {exc}", file=sys.stderr)
        raise
