# Content: how digests are created, stored, and edited

Every episode digest (one-liner, summary, takeaways, highlights, topics) lives
in two places:

- **DB** — the `lex_digest__episodes` table in `~/.rome/default/rome.db`. This
  is what the app serves.
- **Repo** — one markdown file per episode under `data/digests/`
  (`NNN-<slug>.md`). This is the reviewable, diffable, editable copy.

`scripts/sync_digests.mjs` keeps them equal. Neither side is authoritative by
timestamp; whichever direction you run last wins, so run `status` first if
unsure.

## Pipeline

1. **Feed check.** The platform routine `lex-digest-feed-check` runs
   `lex_digest_check_feed` every 2 hours. New RSS entries become `pending`
   rows in the episodes table.
2. **Summarize.** `lex_digest_summarize_episode` fetches the transcript from
   lexfridman.com (falling back to `https://lexfridman.com/<slug>-transcript/`
   when the feed omits the link, and to show notes when no transcript exists
   yet), then runs the `lex-digester` agent with a structured output schema.
   The agent returns the one-liner, summary paragraphs, 5-9 takeaways, 4-7
   verbatim highlight quotes with transcript timestamps, and topic tags. The
   action recomputes each highlight's YouTube second offset from its timestamp
   and writes everything to the DB.
3. **Upgrade.** Episodes digested from show notes are re-checked on every feed
   run with `requireTranscript: true`; once the transcript publishes, they are
   re-digested from it.
4. **Sync to repo.** `node scripts/sync_digests.mjs dump` writes every
   completed episode to `data/digests/`.
5. **Edit.** Edit the markdown files (see the style bar below), then
   `node scripts/sync_digests.mjs load` to push the edits into the DB. The app
   picks them up immediately; no reinstall needed for content changes.

## Sync script

```
node scripts/sync_digests.mjs dump   [--slug <slug>]             # DB -> files
node scripts/sync_digests.mjs load   [--slug <slug>] [--dry-run] # files -> DB
node scripts/sync_digests.mjs status                             # diff both sides
```

Rules:

- Only `completed` episodes are dumped.
- `load` writes editorial fields only: one-liner, summary, takeaways,
  highlights, topics. Front-matter identity fields and the Chapters section
  are DB-owned (chapters come from the transcript) and are ignored on load.
- Rows are matched by `guid`. Files without a matching row are skipped;
  episodes are only ever created by the feed check.
- Highlight `t` offsets are recomputed from the timestamp on load.
- DB path override: `--db <path>` or `LEX_DIGEST_DB` env.

File format (parsed by the script — keep the shape):

- Front matter: `key: <JSON value>` lines between `---` fences.
- `# One-liner`, `# Summary` — plain paragraphs.
- `# Takeaways` — `## <title>` then a detail paragraph.
- `# Highlights` — `## <speaker> @ <timestamp>`, a `>` blockquote, and an
  optional `Context: ...` line. Quotes are verbatim from the transcript; edit
  trims only, never wording, and never change timestamps.

## Style bar

Digest prose follows the no-ai-slop editing skill
(github.com/petergyang/no-ai-slop). The digester agent prompt
(`src/agents/digester.yaml`) encodes the same rules, so new episodes should
arrive mostly clean; the dump-edit-load loop is for what slips through. In
short:

- Concrete over abstract: names, numbers, dates, mechanisms. "Fermilab made
  roughly a nanogram of antimatter per year" beats "antimatter is very hard
  to produce".
- Active voice. Attribute every claim to the speaker who made it.
- Cut banned words (delve, transformative, sweeping, landmark, pivotal,
  leverage...), binary contrasts ("not X but Y"), interpretive signposting
  ("A major thread is..."), and importance puffery.
- Em dashes sparingly — at most one per paragraph, and only when it beats a
  comma, colon, or period.
- Never edit quote wording or timestamps. Fidelity to the transcript outranks
  style.

Applied to episodes #496-#500 on 2026-08-18; the diffs in `data/digests/` from
that date are worked examples.
