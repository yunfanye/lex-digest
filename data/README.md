# Lex Fridman Podcast — Full Transcript Corpus (#1–#500)

Downloaded 2026-08-18. 500 episodes, one markdown file each, ~72 MB total.

## Layout

- `digests/NNN-<slug>.md` — repo copy of each episode's generated digest
  (one-liner, summary, takeaways, highlights, topics). Synced both ways with
  the DB via `scripts/sync_digests.mjs`; see `docs/CONTENT.md`.
- `transcripts/NNN-<slug>.md` — one file per episode. YAML front-matter
  (`episode`, `title`, `guest`, `published`, `source`, `source_url`, `quality`)
  followed by timestamped text. Official transcripts keep speaker labels and
  chapter headings; machine transcripts are merged into ~60-second
  `**[HH:MM:SS]**` blocks (chapter headings where the source provided them).
- `manifest.json` — 500-row index: file, title, guest, date, episode/YouTube
  URLs, source, quality, size.
- `work/` — retrieval scripts (`fetch_official.py`, `fetch_lawwu.py`,
  `fetch_podscripts.py`), the unified `meta.json` episode metadata, and run logs.
  Re-run any script with episode numbers as args to refresh.

## Source hierarchy (per the coverage guides)

| Range | Source | Quality |
|---|---|---|
| #1–#325 (319 eps) | HuggingFace `nmac/lex_fridman_podcast` (Whisper Large) | machine |
| #100 | Happy Scribe via Wayback Machine | machine |
| #268, #282, #283, #287, #291 | PodScripts.co | machine |
| #326–#384 (59 eps) | `lawwu/transcripts` Whisper archive (ggml-large-v2) | machine |
| #385–#500 except #478 (115 eps) | Official lexfridman.com transcripts | human |
| #478 (Scott Horton) | PodScripts.co (no official transcript exists) | machine |

Totals: 115 human / 385 machine.

## Notes

- Episode numbering for the un-numbered early feed era (#1–#71, #84, #98) was
  assigned by publication order anchored to numbered episodes and cross-checked
  against the HF dataset's guest names and the official podcast index.
- #386 uses `marc-andreessen-2-transcript` (the RSS/pack URL 404s).
- Machine transcripts may contain STT errors (names, terms, speaker boundaries).
- Copyright: transcripts are for personal/local use. Public availability does
  not grant redistribution rights — do not republish transcript bodies.
