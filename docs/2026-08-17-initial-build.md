# 2026-08-17 — Initial build

## What

Lex Digest v0.1.0: subscribes to the Lex Fridman Podcast RSS feed
(https://lexfridman.com/feed/podcast/), stores episodes, and generates
transcript-based digests (one-liner, summary paragraphs, 5–9 takeaways,
4–7 verbatim highlight quotes with timestamps, topic tags) via the
`lex-digester` app agent (tier medium, structured outputSchema).

## Decisions

- Transcript source: the RSS description embeds the canonical
  `https://lexfridman.com/<slug>-transcript/` link; transcript pages are
  parsed from `ts-segment` spans (speaker / timestamp / text) plus
  `<h2 id="chapterN_...">` chapter headings, walked in document order so
  segments know their chapter. YouTube ID from the embed URL enables
  `watch?v=ID&t=S` deep links on quotes and chapters.
- Long transcripts (~170k chars typical) are sent whole up to 300k chars;
  beyond that head/tail are kept with an explicit trim marker.
- If no transcript is published yet, the digest is generated from show
  notes and marked `summarySource=shownotes`; a later re-summarize
  upgrades it. `check_feed` retries `failed` episodes each run.
- New-episode detection: guid not stored AND pubDate newer than newest
  stored row (so the initial 5-episode backfill doesn't make older feed
  items look new later). Backfill = `check_feed { maxNew: 5 }`.
- Recurring execution: platform routine `lex-digest-feed-check`
  (FREQ=HOURLY;INTERVAL=2) invoking `lex_digest_check_feed` — registered
  at setup time from the orchestrator, dedup-guarded.
- API POST routes are guardian-gated and dispatch detached action runs;
  the UI polls `/state` every 5s only while work is in flight.

## Validation

- Live parse of the real feed + episode #500 transcript during development.
- `tsc --noEmit`, `pnpm build`, install, backfill run, browser smoke test,
  independent verifier (see final handoff).
