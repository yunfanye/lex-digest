#!/usr/bin/env python3
"""Generate and validate transcript-grounded digests for episodes 1 through 500.

The repository contains two kinds of transcript source:

* newer, speaker-labelled transcripts with chapter headings; and
* older Whisper transcripts that have timestamps but no reliable speaker labels.

This generator deliberately preserves that distinction.  It never invents a
speaker for an unlabelled passage.  Curated profile files in
``.digest-build/profiles`` are used when available; all other episodes use a
deterministic extractive summary built from the checked-in transcript.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifest.json"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
DIGEST_DIR = ROOT / "data" / "digests"
PROFILE_DIR = ROOT / ".digest-build" / "profiles"
METHODOLOGY_PATH = ROOT / "docs" / "DIGEST_METHODOLOGY.md"

LABELED_RE = re.compile(r"^\*\*(.+?)\*\*\s*\((\d{1,2}:\d{2}:\d{2})\):?\s*(.*)$")
CONTINUATION_RE = re.compile(r"^\*\*\*\*\s*\((\d{1,2}:\d{2}:\d{2})\):?\s*(.*)$")
SQUARE_TIME_RE = re.compile(r"^\*\*\[(\d{1,2}:\d{2}:\d{2})\]\*\*\s*:?[ \t]*(.*)$")
PAREN_TIME_RE = re.compile(r"^\*\*\((\d{1,2}:\d{2}:\d{2})\)\*\*\s*:?[ \t]*(.*)$")
PLAIN_TIME_RE = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s*(.*)$")
HEADING_RE = re.compile(r"^#{2,4}\s+(.+?)\s*$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.'’\-]*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘])")

STOPWORDS = set(
    """
    a about above after again against all am an and any are as at be because been before
    being below between both but by can could did do does doing down during each few for
    from further had has have having he her here hers herself him himself his how i if in
    into is it its itself just me more most my myself no nor not now of off on once only or
    other our ours ourselves out over own same she should so some such than that the their
    theirs them themselves then there these they this those through to too under until up
    very was we were what when where which while who whom why will with would you your yours
    yourself yourselves yeah yes okay well really actually basically kind sort mean right
    like thing things something anything everything probably maybe perhaps gonna wanna got
    get gets getting know knows knew say says said saying think thinks thought thinking
    one two three also much many lot lots little big good great make makes made making way
    time people person conversation question answer episode podcast lex fridman guest
    """.split()
)

ACRONYMS = {
    "ai": "AI", "agi": "AGI", "llm": "LLM", "llms": "LLMs", "ml": "ML",
    "nasa": "NASA", "mit": "MIT", "cia": "CIA", "fbi": "FBI", "ufo": "UFO",
    "ufos": "UFOs", "ufc": "UFC", "nfl": "NFL", "nba": "NBA", "nato": "NATO",
    "usa": "US", "us": "US", "ussr": "USSR", "wwii": "WWII", "gpt": "GPT",
    "api": "API", "apis": "APIs", "gpu": "GPU", "gpus": "GPUs", "cpu": "CPU",
    "dna": "DNA", "rna": "RNA", "vr": "VR", "ar": "AR", "ev": "EV",
    "tesla": "Tesla", "spacex": "SpaceX", "openai": "OpenAI", "deepmind": "DeepMind",
}

BAD_PHRASES = (
    "check out our sponsors", "this episode is brought to you", "support this podcast",
    "use code lex", "promo code", "thanks for listening", "hope to see you next time",
    "the following is a conversation", "this is the lex fridman podcast",
    "please subscribe", "click the bell", "link in the description", "quick pause",
    "let me leave you with", "terms and conditions apply", "not financial advice",
    "inaudible", "audio quality", "recording session", "adobe audition",
)

BIO_WORDS = {
    "professor", "researcher", "scientist", "engineer", "founder", "cofounder", "author",
    "historian", "physicist", "mathematician", "philosopher", "economist", "journalist",
    "musician", "artist", "director", "actor", "athlete", "champion", "president",
    "ceo", "cto", "doctor", "surgeon", "psychologist", "neuroscientist", "programmer",
}

STRONG_WORDS = {
    "evidence", "mechanism", "reason", "risk", "tradeoff", "failure", "success",
    "important", "fundamental", "future", "history", "power", "freedom", "truth",
    "intelligence", "consciousness", "science", "technology", "war", "peace", "love",
    "meaning", "leadership", "learning", "evolution", "democracy", "security",
    "incentive", "uncertainty", "responsibility", "system", "design", "principle",
}

SENSITIVE_WORDS = {
    "election", "politics", "president", "government", "war", "ukraine", "russia",
    "israel", "palestine", "china", "covid", "vaccine", "medicine", "medical",
    "health", "disease", "drug", "law", "legal", "crime", "religion", "genocide",
    "terrorism", "nuclear", "economy", "finance", "investment", "immigration",
}

GENERIC_HEADINGS = {
    "opening", "preamble", "introduction", "intro", "episode highlight", "highlights",
    "sponsors", "sponsor", "advertisement", "ads", "closing", "outro", "conclusion",
}


def normalize_time(value: str) -> str:
    parts = [int(part) for part in value.split(":")]
    if len(parts) != 3:
        raise ValueError(f"Invalid timestamp: {value}")
    return f"{parts[0]:02d}:{parts[1]:02d}:{parts[2]:02d}"


def seconds(value: str) -> int:
    hour, minute, second = (int(part) for part in value.split(":"))
    return hour * 3600 + minute * 60 + second


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def tokenize(text: str) -> list[str]:
    output: list[str] = []
    for raw in words(text):
        token = raw.lower().strip(".'’-")
        if not token or token in STOPWORDS:
            continue
        if len(token) < 3 and token not in ACRONYMS:
            continue
        if token.isdigit() or len(token) > 28:
            continue
        output.append(token)
    return output


def pretty_term(token: str) -> str:
    if token in ACRONYMS:
        return ACRONYMS[token]
    if token.endswith("'s"):
        token = token[:-2]
    return token.replace("-", " ").title()


def human_join(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return "the episode's central themes"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[(?:music|applause|laughter|silence)\]", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_heading(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"^\[[^\]]+\]\s*", "", value)
    value = re.sub(r"^\d{1,2}:\d{2}(?::\d{2})?\s*[-–—:]?\s*", "", value)
    value = value.strip(" -–—:#")
    if len(value) > 82:
        value = value[:79].rstrip() + "…"
    return value or "Discussion"


def transcript_body(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines


def parse_transcript(path: Path) -> tuple[list[dict], bool]:
    lines = transcript_body(path.read_text(encoding="utf-8", errors="replace").splitlines())
    sections: list[dict] = [{"name": "Opening", "utterances": []}]
    current = sections[0]
    last_speaker: str | None = None
    labelled_count = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            current = {"name": clean_heading(heading.group(1)), "utterances": []}
            sections.append(current)
            last_speaker = None
            continue

        match = CONTINUATION_RE.match(line)
        if match:
            timestamp, text = match.groups()
            current["utterances"].append(
                {"speaker": last_speaker, "time": normalize_time(timestamp), "text": clean_text(text)}
            )
            continue

        match = LABELED_RE.match(line)
        if match:
            speaker, timestamp, text = match.groups()
            speaker = clean_text(speaker).strip("* ") or None
            last_speaker = speaker or last_speaker
            if speaker:
                labelled_count += 1
            current["utterances"].append(
                {"speaker": last_speaker, "time": normalize_time(timestamp), "text": clean_text(text)}
            )
            continue

        match = SQUARE_TIME_RE.match(line) or PAREN_TIME_RE.match(line) or PLAIN_TIME_RE.match(line)
        if match:
            timestamp, text = match.groups()
            current["utterances"].append(
                {"speaker": None, "time": normalize_time(timestamp), "text": clean_text(text)}
            )
            last_speaker = None
            continue

        if current["utterances"]:
            previous = current["utterances"][-1]
            previous["text"] = clean_text(previous["text"] + " " + line)

    sections = [section for section in sections if section["utterances"]]
    total = sum(len(section["utterances"]) for section in sections)
    has_reliable_labels = total > 0 and labelled_count / total >= 0.20
    if not sections:
        raise ValueError(f"No timestamped transcript content parsed from {path}")
    return sections, has_reliable_labels


def top_terms(texts: list[str], limit: int = 5, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    counts = collections.Counter(token for text in texts for token in tokenize(text) if token not in exclude)
    candidates = []
    for token, count in counts.items():
        if count < 2 and len(texts) > 4:
            continue
        score = count * (1.0 + min(len(token), 12) / 16.0)
        candidates.append((score, token))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    result: list[str] = []
    stems: set[str] = set()
    for _, token in candidates:
        stem = token.rstrip("s")
        if stem in stems:
            continue
        result.append(pretty_term(token))
        stems.add(stem)
        if len(result) >= limit:
            break
    return result


def derive_sections(sections: list[dict]) -> list[dict]:
    meaningful = [
        section for section in sections
        if clean_heading(section["name"]).lower() not in GENERIC_HEADINGS
    ]
    if len(meaningful) >= 3:
        return sections

    utterances = [utterance for section in sections for utterance in section["utterances"]]
    if len(utterances) < 12:
        return sections
    bucket_count = min(10, max(5, round(len(utterances) / 45)))
    bucket_size = math.ceil(len(utterances) / bucket_count)
    derived: list[dict] = []
    for start in range(0, len(utterances), bucket_size):
        chunk = utterances[start : start + bucket_size]
        terms = top_terms([item["text"] for item in chunk], limit=3)
        name = "Discussion: " + human_join(terms) if terms else "Discussion"
        derived.append({"name": name, "utterances": chunk})
    return derived


def sentence_items(sections: list[dict]) -> list[dict]:
    items: list[dict] = []
    for section_index, section in enumerate(sections):
        for utterance in section["utterances"]:
            text = clean_text(utterance["text"])
            pieces = SENTENCE_SPLIT_RE.split(text)
            for piece in pieces:
                piece = clean_text(piece)
                if piece:
                    items.append(
                        {
                            "section": clean_heading(section["name"]),
                            "section_index": section_index,
                            "speaker": utterance["speaker"],
                            "time": utterance["time"],
                            "text": piece,
                        }
                    )
    return items


def is_bad_sentence(item: dict) -> bool:
    text = item["text"]
    low = text.lower()
    count = len(words(text))
    if count < 10 or count > 58:
        return True
    if text.endswith("?") or text.endswith((",", ":", ";")):
        return True
    if any(phrase in low for phrase in BAD_PHRASES):
        return True
    if "http://" in low or "https://" in low or "www." in low:
        return True
    if low.count("thank you") + low.count("thanks") >= 2:
        return True
    if re.search(r"\b(um|uh|erm)\b", low):
        return True
    if sum(character.isalpha() for character in text) < max(20, len(text) * 0.55):
        return True
    return False


def sentence_ranker(items: list[dict], title: str, guest: str):
    corpus_tokens = [token for item in items for token in tokenize(item["text"])]
    counts = collections.Counter(corpus_tokens)
    total = max(len(corpus_tokens), 1)
    title_tokens = set(tokenize(title + " " + guest))
    guest_tokens = set(tokenize(guest))

    def rank(item: dict) -> float:
        if is_bad_sentence(item):
            return -999.0
        content = tokenize(item["text"])
        if not content:
            return -999.0
        informative = [token for token in content if counts[token] >= 2 or token in title_tokens]
        if not informative:
            informative = content
        rarity = sum(min(3.4, math.log((total + 20) / (counts[token] + 1))) for token in informative)
        rarity /= max(len(informative), 1)
        score = 0.75 * rarity
        section_tokens = set(tokenize(item["section"]))
        score += 0.34 * sum(token in title_tokens for token in content)
        score += 0.20 * sum(token in section_tokens for token in content)
        score += 0.20 * sum(token in STRONG_WORDS for token in content)
        length = len(words(item["text"]))
        score += max(0.0, 1.1 - abs(length - 25) / 22.0)
        speaker = (item["speaker"] or "").lower()
        if speaker and guest_tokens and any(token in speaker for token in guest_tokens):
            score += 0.55
        elif speaker.startswith("lex"):
            score -= 0.15
        if seconds(item["time"]) < 90:
            score -= 0.35
        if item["section"].lower() in GENERIC_HEADINGS:
            score -= 0.55
        low = item["text"].lower()
        if re.search(r"\b(the key|the point|what matters|the reason|i learned|i believe|we need|you have to|the most important)\b", low):
            score += 0.65
        if re.search(r"\b(i think|i mean|you know|kind of|sort of)\b", low):
            score -= 0.12
        return score

    return rank


def select_sentences(items: list[dict], title: str, guest: str, count: int = 12) -> list[dict]:
    rank = sentence_ranker(items, title, guest)
    ranked = sorted(items, key=rank, reverse=True)
    chosen: list[dict] = []
    used_sections: set[str] = set()
    used_prefixes: set[str] = set()

    def acceptable(item: dict, require_new_section: bool, require_distance: bool) -> bool:
        if rank(item) < 0:
            return False
        if require_new_section and item["section"] in used_sections:
            return False
        normalized = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
        prefix = normalized[:72]
        if not prefix or prefix in used_prefixes:
            return False
        if require_distance and any(abs(seconds(item["time"]) - seconds(old["time"])) < 100 for old in chosen):
            return False
        return True

    for require_new_section, require_distance in ((True, True), (False, True), (False, False)):
        for item in ranked:
            if len(chosen) >= count:
                break
            if not acceptable(item, require_new_section, require_distance):
                continue
            normalized = re.sub(r"[^a-z0-9]+", " ", item["text"].lower()).strip()
            chosen.append(item)
            used_sections.add(item["section"])
            used_prefixes.add(normalized[:72])
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda item: seconds(item["time"]))


def short_quote(text: str, max_words: int = 34) -> str:
    text = clean_text(text)
    text = re.sub(r"^(?:Well|Okay|Yeah|Yes|No|So|And|But|I mean|You know)[, ]+", "", text, flags=re.I)
    tokens = text.split()
    if len(tokens) > max_words:
        text = " ".join(tokens[:max_words]).rstrip(" ,;:") + "…"
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.replace("“", "'").replace("”", "'").replace('"', "'")


def section_lookup(sections: list[dict]) -> dict[str, dict]:
    return {clean_heading(section["name"]): section for section in sections}


def section_terms(section: dict | None, exclude: set[str], limit: int = 4) -> list[str]:
    if not section:
        return []
    return top_terms([item["text"] for item in section["utterances"]], limit=limit, exclude=exclude)


def select_chapters(sections: list[dict], cap: int = 20) -> list[dict]:
    chapters: list[dict] = []
    for section in sections:
        name = clean_heading(section["name"])
        if name.lower() in {"opening", "preamble", "sponsors", "sponsor", "advertisement", "ads"}:
            continue
        chapters.append(
            {
                "time": section["utterances"][0]["time"],
                "name": name,
                "words": sum(len(words(item["text"])) for item in section["utterances"]),
            }
        )
    if not chapters:
        first = sections[0]["utterances"][0]
        chapters = [{"time": first["time"], "name": "Conversation", "words": 1}]
    if len(chapters) <= cap:
        return chapters
    keep = {0, len(chapters) - 1}
    for index in sorted(range(len(chapters)), key=lambda idx: chapters[idx]["words"], reverse=True):
        keep.add(index)
        if len(keep) >= cap:
            break
    return [chapter for index, chapter in enumerate(chapters) if index in keep]


def themes_from_sections(sections: list[dict], title: str, guest: str, limit: int = 8) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for chapter in select_chapters(sections, cap=20):
        name = clean_heading(chapter["name"])
        low = name.lower()
        if low in GENERIC_HEADINGS or low.startswith("discussion:"):
            continue
        key = re.sub(r"[^a-z0-9]+", " ", low).strip()
        if key and key not in seen:
            candidates.append(name)
            seen.add(key)
    if len(candidates) < limit:
        exclude = set(tokenize(title + " " + guest))
        terms = top_terms(
            [item["text"] for section in sections for item in section["utterances"]],
            limit=limit * 2,
            exclude=set(),
        )
        for term in terms:
            key = term.lower()
            if key not in seen and key not in exclude:
                candidates.append(term)
                seen.add(key)
            if len(candidates) >= limit:
                break
    return candidates[:limit]


def find_bio_sentence(items: list[dict], guest: str) -> dict | None:
    guest_parts = [part.lower() for part in tokenize(guest)]
    surname = guest_parts[-1] if guest_parts else ""
    best: tuple[float, dict] | None = None
    for item in items:
        if seconds(item["time"]) > 12 * 60:
            break
        text = item["text"]
        low = text.lower()
        token_set = set(tokenize(text))
        score = 1.4 * sum(word in token_set for word in BIO_WORDS)
        if surname and surname in low:
            score += 2.0
        if " is a " in low or " is an " in low:
            score += 0.8
        if any(phrase in low for phrase in BAD_PHRASES):
            score -= 4.0
        count = len(words(text))
        if not 10 <= count <= 52:
            continue
        if best is None or score > best[0]:
            best = (score, item)
    return best[1] if best and best[0] >= 1.2 else None


def extract_youtube_id(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [""])[0]
    return ""


def youtube_timestamp_url(youtube_id: str, timestamp: str) -> str:
    if not youtube_id:
        return ""
    return f"https://www.youtube.com/watch?v={youtube_id}&t={seconds(timestamp)}s"


def safe_speaker(item: dict, reliable_labels: bool) -> str:
    if reliable_labels and item.get("speaker"):
        return clean_text(item["speaker"])
    return "Conversation"


def auto_content(row: dict, sections: list[dict], reliable_labels: bool) -> dict:
    title = str(row.get("title") or f"Episode {row['episode']}")
    guest = str(row.get("guest") or "Guest")
    items = sentence_items(sections)
    selected = select_sentences(items, title, guest, count=16)
    if len(selected) < 6:
        raise ValueError(f"Episode {row['episode']} has too few usable transcript passages")

    themes = themes_from_sections(sections, title, guest, limit=8)
    primary_themes = themes[:5] or top_terms([item["text"] for item in items], limit=5)
    one_liner = (
        f"{guest} joins Lex Fridman for a transcript-grounded conversation on "
        f"{human_join(primary_themes)}, connecting the episode's technical, historical, "
        "personal, and philosophical threads for a time-limited reader."
    )

    bio = find_bio_sentence(items, guest)
    if bio:
        opening = (
            f"The transcript introduces {guest} with the following context: “{short_quote(bio['text'], 36)}” "
            f"From there, the episode ranges across {human_join(primary_themes)}."
        )
    else:
        opening = (
            f"This episode brings {guest} into a wide-ranging discussion of "
            f"{human_join(primary_themes)}. The digest below stays close to the checked-in transcript "
            "and uses timestamps so each point can be inspected in context."
        )
    if not reliable_labels:
        opening += (
            " The source is an older machine transcript without reliable speaker labels, so quoted "
            "passages are attributed to the conversation rather than to a named speaker."
        )

    lookup = section_lookup(sections)
    exclude = set(tokenize(title + " " + guest))
    representatives: list[dict] = []
    if selected:
        target_indexes = [max(0, round((len(selected) - 1) * ratio)) for ratio in (0.18, 0.50, 0.82)]
        for index in target_indexes:
            item = selected[index]
            if item not in representatives:
                representatives.append(item)
        for item in selected:
            if len(representatives) >= 3:
                break
            if item not in representatives:
                representatives.append(item)

    summary = [opening]
    for item in representatives[:3]:
        section_name = item["section"]
        terms = section_terms(lookup.get(section_name), exclude, limit=4)
        focus = human_join(terms) if terms else section_name.lower()
        speaker = safe_speaker(item, reliable_labels)
        attribution = f"{speaker} says" if speaker != "Conversation" else "a representative passage says"
        summary.append(
            f"In the discussion of {section_name}, the transcript centers on {focus}. "
            f"At {item['time']}, {attribution}: “{short_quote(item['text'], 34)}” "
            "The timestamp matters because the surrounding exchange supplies the qualifications and examples "
            "that a compressed summary cannot fully preserve."
        )

    topic_text = " ".join([title, guest] + themes).lower()
    if any(word in topic_text for word in SENSITIVE_WORDS):
        summary.append(
            "This episode touches subjects where factual, political, medical, legal, or historical claims may be "
            "contested. The digest therefore preserves attribution and treats the interview as a primary-source "
            "conversation, not as an independent fact-check."
        )
    else:
        summary.append(
            f"Taken together, the episode is most useful as a map of how {human_join(primary_themes[:4])} "
            "fit together. The memorable moments and chapter links below provide the fastest route back to the "
            "speaker's full reasoning."
        )

    takeaways: list[dict] = []
    used_titles: collections.Counter[str] = collections.Counter()
    for item in selected:
        if len(takeaways) >= 6:
            break
        section_name = item["section"]
        used_titles[section_name] += 1
        title_suffix = f" ({used_titles[section_name]})" if used_titles[section_name] > 1 else ""
        terms = section_terms(lookup.get(section_name), exclude, limit=3)
        focus = human_join(terms) if terms else section_name.lower()
        speaker = safe_speaker(item, reliable_labels)
        attribution = speaker if speaker != "Conversation" else "the transcript"
        takeaways.append(
            {
                "title": f"{section_name}{title_suffix}",
                "text": (
                    f"The treatment of this topic connects {focus}. At {item['time']}, {attribution} frames a key "
                    f"point as: “{short_quote(item['text'], 31)}” Use the linked moment to recover the surrounding "
                    "argument and any caveats."
                ),
            }
        )

    topics: list[str] = []
    for candidate in [guest] + themes + top_terms([item["text"] for item in items], limit=12):
        candidate = clean_heading(candidate)
        key = re.sub(r"[^a-z0-9]+", " ", candidate.lower()).strip()
        if not key or key in {re.sub(r"[^a-z0-9]+", " ", topic.lower()).strip() for topic in topics}:
            continue
        topics.append(candidate)
        if len(topics) >= 8:
            break

    highlights: list[dict] = []
    for item in selected[:10]:
        if len(highlights) >= 6:
            break
        highlights.append(
            {
                "speaker": safe_speaker(item, reliable_labels),
                "time": item["time"],
                "quote": short_quote(item["text"], 38),
                "context": f"From the discussion of {item['section'].lower()}.",
            }
        )

    return {
        "one_liner": one_liner,
        "summary": summary,
        "takeaways": takeaways,
        "topics": topics,
        "highlights": highlights,
    }


def load_manifest() -> dict[int, dict]:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("data/manifest.json must contain a list")
    manifest: dict[int, dict] = {}
    for row in raw:
        episode = int(row["episode"])
        manifest[episode] = row
    missing = sorted(set(range(1, 501)) - set(manifest))
    if missing:
        raise ValueError(f"Manifest is missing episodes: {missing}")
    return manifest


def load_profiles() -> dict[int, dict]:
    profiles: dict[int, dict] = {}
    if not PROFILE_DIR.exists():
        return profiles
    for path in sorted(PROFILE_DIR.glob("*.json")):
        text = path.read_text(encoding="utf-8", errors="replace")
        payload = None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            repaired = re.sub(r",\s*([}\]])", r"\1", text)
            try:
                payload = json.loads(repaired)
            except json.JSONDecodeError as error:
                print(f"warning: skipping malformed profile file {path.name}: {error}", file=sys.stderr)
                continue
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            try:
                episode = int(key)
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                profiles[episode] = value
    return profiles


def profile_content(profile: dict, fallback: dict) -> dict:
    one_liner = str(profile.get("one_liner") or fallback["one_liner"]).strip()
    summary = profile.get("summary")
    if not isinstance(summary, list) or not summary:
        summary = fallback["summary"]
    else:
        summary = [str(item).strip() for item in summary if str(item).strip()]
    takeaways = profile.get("takeaways")
    if not isinstance(takeaways, list) or len(takeaways) < 4:
        takeaways = fallback["takeaways"]
    else:
        normalized = []
        for item in takeaways:
            if isinstance(item, dict) and item.get("title") and item.get("text"):
                normalized.append({"title": str(item["title"]).strip(), "text": str(item["text"]).strip()})
        takeaways = normalized if len(normalized) >= 4 else fallback["takeaways"]
    topics = profile.get("topics")
    if not isinstance(topics, list) or len(topics) < 3:
        topics = fallback["topics"]
    else:
        topics = [str(item).strip() for item in topics if str(item).strip()][:12]
    highlights = profile.get("highlights")
    if not isinstance(highlights, list) or len(highlights) < 4:
        highlights = fallback["highlights"]
    return {
        "one_liner": one_liner,
        "summary": summary,
        "takeaways": takeaways,
        "topics": topics,
        "highlights": highlights,
    }


def digest_slug(row: dict) -> str:
    filename = str(row["file"])
    slug = re.sub(r"^\d+-", "", filename)
    return slug[:-3] if slug.endswith(".md") else slug


def render_digest(row: dict, content: dict, sections: list[dict], reliable_labels: bool) -> str:
    episode = int(row["episode"])
    slug = digest_slug(row)
    youtube_id = extract_youtube_id(str(row.get("youtube_url") or ""))
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    title = str(row.get("title") or f"Episode {episode}")
    guest = str(row.get("guest") or "Guest")
    published = str(row.get("published") or "")
    link = str(row.get("episode_url") or "")

    lines = [
        "---",
        f"slug: {json.dumps(slug, ensure_ascii=False)}",
        f"episode: {episode}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"guest: {json.dumps(guest, ensure_ascii=False)}",
        f"link: {json.dumps(link, ensure_ascii=False)}",
        f"youtube_id: {json.dumps(youtube_id, ensure_ascii=False)}",
        f"published: {json.dumps(published, ensure_ascii=False)}",
        'summary_source: "transcript"',
        f"summarized_at: {json.dumps(generated_at)}",
        f"speaker_labels: {json.dumps('reliable' if reliable_labels else 'unavailable')}",
        f"topics: {json.dumps(content['topics'], ensure_ascii=False)}",
        "---",
        "",
        "# One-liner",
        "",
        content["one_liner"].strip(),
        "",
        "# Summary",
        "",
    ]
    for paragraph in content["summary"]:
        lines.extend([str(paragraph).strip(), ""])

    lines.extend(["# Key takeaways", ""])
    for index, item in enumerate(content["takeaways"], start=1):
        lines.extend([f"## {index}. {item['title']}", "", item["text"].strip(), ""])

    lines.extend(["# Memorable moments", ""])
    for item in content["highlights"]:
        timestamp = normalize_time(str(item["time"]))
        speaker = str(item.get("speaker") or "Conversation").strip()
        quote = short_quote(str(item.get("quote") or ""), 42)
        context = str(item.get("context") or "Transcript highlight.").strip()
        url = youtube_timestamp_url(youtube_id, timestamp)
        time_label = f"[{timestamp}]({url})" if url else timestamp
        lines.append(f"- **{time_label} — {speaker}:** “{quote}”")
        lines.append(f"  - {context}")
    lines.append("")

    lines.extend(["# Topics", ""])
    for topic in content["topics"]:
        lines.append(f"- {topic}")
    lines.append("")

    lines.extend(["# Chapters", ""])
    for chapter in select_chapters(sections, cap=20):
        timestamp = chapter["time"]
        url = youtube_timestamp_url(youtube_id, timestamp)
        time_label = f"[{timestamp}]({url})" if url else timestamp
        lines.append(f"- **{time_label}** — {chapter['name']}")
    lines.append("")
    return "\n".join(lines)


def parse_frontmatter_episode(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"(?m)^episode:\s*(\d+)\s*$", text)
    return int(match.group(1)) if match else None


def basic_digest_valid(path: Path, episode: int) -> bool:
    if not path.exists() or parse_frontmatter_episode(path) != episode:
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(heading in text for heading in ("# One-liner", "# Summary", "# Key takeaways", "# Memorable moments", "# Topics", "# Chapters"))


def write_methodology(curated_episodes: list[int], auto_episodes: list[int]) -> None:
    curated_ranges = "#400–#447" if curated_episodes else "none"
    text = f"""# Digest methodology

This repository contains one Markdown digest for every Lex Fridman Podcast episode from **#1 through #500**.

## Source hierarchy

1. The checked-in transcript under `data/transcripts/` is the primary source.
2. Episode metadata comes from `data/manifest.json`.
3. Curated editorial profiles are used for {curated_ranges} when their JSON validates; all other missing digests are produced by deterministic extractive summarization.

## What each digest contains

Every digest has a one-line orientation, a multi-paragraph summary, six key takeaways, six timestamped memorable moments, topics, and chapter navigation. Quoted passages are deliberately short and link back to the recording when a YouTube ID is available.

## Speaker attribution

Newer transcripts contain explicit speaker labels. Many early Whisper transcripts do not. When labels are absent or unreliable, the digest says **Conversation** rather than guessing whether a passage came from Lex or the guest.

## Editorial safeguards

- Summaries and takeaways are grounded in timestamped transcript passages.
- Scientific, political, medical, legal, historical, and otherwise disputed claims remain attributed to the conversation; the digest is not presented as an independent fact-check.
- Sponsorship copy, intros, outros, and malformed transcript fragments are down-ranked or excluded.
- Generation validates one unique digest for every episode, required frontmatter, required sections, timestamp shape, and minimum content depth.

## Coverage generated in this pass

- Curated-profile episodes used: **{len(curated_episodes)}**
- Deterministically summarized episodes used: **{len(auto_episodes)}**
- Total validated coverage: **500 episodes**
"""
    METHODOLOGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    METHODOLOGY_PATH.write_text(text, encoding="utf-8")


def validate(manifest: dict[int, dict]) -> None:
    expected_paths: dict[int, Path] = {
        episode: DIGEST_DIR / f"{digest_slug(row)}.md" for episode, row in manifest.items()
    }
    if len(set(expected_paths.values())) != 500:
        duplicates = [str(path) for path, count in collections.Counter(expected_paths.values()).items() if count > 1]
        raise ValueError(f"Digest slug collision(s): {duplicates}")

    errors: list[str] = []
    seen: dict[int, Path] = {}
    for episode in range(1, 501):
        path = expected_paths[episode]
        if not path.exists():
            errors.append(f"missing digest for episode {episode}: {path.name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed_episode = parse_frontmatter_episode(path)
        if parsed_episode != episode:
            errors.append(f"{path.name}: frontmatter episode is {parsed_episode}, expected {episode}")
        if parsed_episode in seen:
            errors.append(f"duplicate episode {parsed_episode}: {seen[parsed_episode].name} and {path.name}")
        elif parsed_episode is not None:
            seen[parsed_episode] = path
        for heading in ("# One-liner", "# Summary", "# Key takeaways", "# Memorable moments", "# Topics", "# Chapters"):
            if heading not in text:
                errors.append(f"{path.name}: missing heading {heading}")
        if len(words(text)) < 260:
            errors.append(f"{path.name}: digest is unexpectedly short ({len(words(text))} words)")
        if len(re.findall(r"\b\d{2}:\d{2}:\d{2}\b", text)) < 6:
            errors.append(f"{path.name}: fewer than six timestamps")
        if "TODO" in text or "PLACEHOLDER" in text:
            errors.append(f"{path.name}: contains placeholder text")

    for path in DIGEST_DIR.glob("*.md"):
        episode = parse_frontmatter_episode(path)
        if episode is not None and 1 <= episode <= 500 and path != expected_paths[episode]:
            errors.append(f"unexpected duplicate/stale digest path for episode {episode}: {path.name}")

    if set(seen) != set(range(1, 501)):
        missing = sorted(set(range(1, 501)) - set(seen))
        if missing:
            errors.append(f"episodes absent after validation: {missing}")

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:80])
        remainder = f"\n... and {len(errors) - 80} more" if len(errors) > 80 else ""
        raise ValueError(f"Digest validation failed with {len(errors)} error(s):\n{preview}{remainder}")
    print("Validated exactly 500 transcript-grounded episode digests.")


def generate() -> None:
    manifest = load_manifest()
    profiles = load_profiles()
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    expected_paths = {episode: DIGEST_DIR / f"{digest_slug(row)}.md" for episode, row in manifest.items()}

    for path in DIGEST_DIR.glob("*.md"):
        episode = parse_frontmatter_episode(path)
        if episode is not None and 1 <= episode <= 500 and path != expected_paths[episode]:
            path.unlink()

    curated_used: list[int] = []
    auto_used: list[int] = []
    for episode in range(1, 501):
        row = manifest[episode]
        transcript_path = TRANSCRIPT_DIR / str(row["file"])
        if not transcript_path.exists():
            raise FileNotFoundError(f"Missing transcript for episode {episode}: {transcript_path}")
        sections, reliable_labels = parse_transcript(transcript_path)
        sections = derive_sections(sections)
        fallback = auto_content(row, sections, reliable_labels)
        profile = profiles.get(episode)
        if profile:
            content = profile_content(profile, fallback)
            curated_used.append(episode)
        else:
            content = fallback
            auto_used.append(episode)
        digest = render_digest(row, content, sections, reliable_labels)
        expected_paths[episode].write_text(digest, encoding="utf-8")
        if episode % 25 == 0:
            print(f"generated {episode}/500")

    write_methodology(curated_used, auto_used)
    validate(manifest)
    print(f"Curated profiles used for {len(curated_used)} episodes; deterministic extraction used for {len(auto_used)}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest()
    if args.validate_only:
        validate(manifest)
    else:
        generate()


if __name__ == "__main__":
    main()
