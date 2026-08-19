#!/usr/bin/env node
/**
 * sync_digests.mjs — two-way sync between the lex-digest DB and data/digests/.
 *
 * The DB (lex_digest__episodes) is the runtime store the app reads. The files
 * under data/digests/ are the repo copy: reviewable, diffable, editable.
 *
 *   node scripts/sync_digests.mjs dump   [--slug <slug>]            DB  -> files
 *   node scripts/sync_digests.mjs load   [--slug <slug>] [--dry-run] files -> DB
 *   node scripts/sync_digests.mjs status                            diff both sides
 *
 * Sync rules:
 * - Only episodes with status "completed" are dumped (others have no content).
 * - `load` updates editorial fields only: one_liner, summary, takeaways,
 *   highlights, topics. Identity fields (guid, title, urls...) and machine
 *   fields (chapters, transcript stats, status) are DB-owned; the file copy of
 *   those is informational and ignored on load.
 * - Highlight `t` (YouTube second offset) is recomputed from the timestamp.
 * - Rows are matched by guid from the file front matter; unknown guids are
 *   skipped with a warning (episodes are created by the RSS check, not here).
 *
 * DB path: --db <path> or LEX_DIGEST_DB env, default ~/.rome/default/rome.db.
 */

import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

function loadBetterSqlite3() {
  const candidates = ["better-sqlite3", "/app/node_modules/better-sqlite3"];
  for (const c of candidates) {
    try {
      return require(c);
    } catch {
      /* try next */
    }
  }
  console.error("better-sqlite3 not found. Install it or run inside the Rome container.");
  process.exit(1);
}

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIGESTS_DIR = path.join(ROOT, "data", "digests");
const TABLE = "lex_digest__episodes";

// ---------------------------------------------------------------------------
// CLI parsing
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const mode = args[0];
const flag = (name) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : undefined;
};
const has = (name) => args.includes(name);

if (!["dump", "load", "status"].includes(mode ?? "")) {
  console.log("Usage: node scripts/sync_digests.mjs <dump|load|status> [--slug <slug>] [--dry-run] [--db <path>]");
  process.exit(mode ? 1 : 0);
}

const dbPath =
  flag("--db") ?? process.env.LEX_DIGEST_DB ?? path.join(os.homedir(), ".rome", "default", "rome.db");
const onlySlug = flag("--slug");
const dryRun = has("--dry-run");

const Database = loadBetterSqlite3();
const db = new Database(dbPath, { readonly: mode !== "load" || dryRun });
db.pragma("busy_timeout = 5000");

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

const pad3 = (n) => String(n ?? 0).padStart(3, "0");
const fileNameFor = (row) => `${pad3(row.episode_number)}-${row.slug}.md`;

function timestampToSeconds(ts) {
  const m = /(\d+):(\d{2}):(\d{2})/.exec(ts ?? "");
  if (!m) return null;
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
}

const isoDate = (unixSeconds) =>
  unixSeconds ? new Date(unixSeconds * 1000).toISOString() : null;

// Front-matter values are JSON-encoded strings/arrays, which is valid YAML and
// round-trips titles containing '#', ':', quotes, etc.
function encodeFrontMatter(obj) {
  const lines = ["---"];
  for (const [k, v] of Object.entries(obj)) {
    if (v === null || v === undefined) continue;
    lines.push(`${k}: ${JSON.stringify(v)}`);
  }
  lines.push("---");
  return lines.join("\n");
}

function parseFrontMatter(text) {
  const m = /^---\n([\s\S]*?)\n---\n?/.exec(text);
  if (!m) throw new Error("missing front matter");
  const meta = {};
  for (const line of m[1].split("\n")) {
    const i = line.indexOf(": ");
    if (i < 0) continue;
    const key = line.slice(0, i);
    const raw = line.slice(i + 2);
    try {
      meta[key] = JSON.parse(raw);
    } catch {
      meta[key] = raw;
    }
  }
  return { meta, body: text.slice(m[0].length) };
}

// ---------------------------------------------------------------------------
// Render: DB row -> markdown
// ---------------------------------------------------------------------------

function renderEpisode(row) {
  const takeaways = JSON.parse(row.takeaways ?? "[]");
  const highlights = JSON.parse(row.highlights ?? "[]");
  const topics = JSON.parse(row.topics ?? "[]");
  const chapters = JSON.parse(row.chapters ?? "[]");

  const fm = encodeFrontMatter({
    guid: row.guid,
    slug: row.slug,
    episode: row.episode_number,
    title: row.title,
    guest: row.guest,
    link: row.link,
    youtube_id: row.youtube_id,
    published: isoDate(row.pub_date)?.slice(0, 10),
    summary_source: row.summary_source,
    summarized_at: isoDate(row.summarized_at),
    topics,
  });

  const out = [fm, ""];

  out.push("# One-liner", "", row.one_liner ?? "", "");
  out.push("# Summary", "", (row.summary ?? "").trim(), "");

  out.push("# Takeaways", "");
  for (const t of takeaways) {
    out.push(`## ${t.title}`, "", (t.detail ?? "").trim(), "");
  }

  out.push("# Highlights", "");
  for (const h of highlights) {
    out.push(`## ${h.speaker} @ ${h.timestamp}`, "");
    for (const line of String(h.quote ?? "").split("\n")) out.push(`> ${line}`);
    out.push("");
    if (h.context) out.push(`Context: ${h.context}`, "");
  }

  // Informational only — chapters come from the transcript and are DB-owned.
  out.push("# Chapters", "");
  for (const c of chapters) out.push(`- [${c.timestamp}] ${c.title}`);
  out.push("");

  return out.join("\n");
}

// ---------------------------------------------------------------------------
// Parse: markdown -> editorial fields
// ---------------------------------------------------------------------------

function splitSections(body) {
  const sections = {};
  let current = null;
  for (const line of body.split("\n")) {
    const h = /^# (.+)$/.exec(line);
    if (h) {
      current = h[1].trim();
      sections[current] = [];
    } else if (current) {
      sections[current].push(line);
    }
  }
  for (const k of Object.keys(sections)) sections[k] = sections[k].join("\n").trim();
  return sections;
}

function parseTakeaways(text) {
  const items = [];
  let current = null;
  for (const line of (text ?? "").split("\n")) {
    const h = /^## (.+)$/.exec(line);
    if (h) {
      if (current) items.push(current);
      current = { title: h[1].trim(), detail: [] };
    } else if (current) {
      current.detail.push(line);
    }
  }
  if (current) items.push(current);
  return items.map((t) => ({ title: t.title, detail: t.detail.join("\n").trim() }));
}

function parseHighlights(text) {
  const items = [];
  let current = null;
  const push = () => {
    if (!current) return;
    items.push(
      canonicalHighlight({
        quote: current.quote.join("\n").trim(),
        speaker: current.speaker,
        timestamp: current.timestamp,
        context: current.context ?? undefined,
        t: timestampToSeconds(current.timestamp),
      }),
    );
  };
  for (const line of (text ?? "").split("\n")) {
    const h = /^## (.+) @ (.+)$/.exec(line);
    if (h) {
      push();
      current = { speaker: h[1].trim(), timestamp: h[2].trim(), quote: [], context: null };
    } else if (current && line.startsWith(">")) {
      current.quote.push(line.replace(/^> ?/, ""));
    } else if (current && line.startsWith("Context: ")) {
      current.context = line.slice("Context: ".length).trim();
    }
  }
  push();
  return items;
}

function parseEpisodeFile(filePath) {
  const { meta, body } = parseFrontMatter(fs.readFileSync(filePath, "utf8"));
  const sections = splitSections(body);
  if (!meta.guid) throw new Error("front matter has no guid");
  return {
    guid: meta.guid,
    slug: meta.slug,
    fields: {
      one_liner: sections["One-liner"] ?? "",
      summary: sections["Summary"] ?? "",
      takeaways: parseTakeaways(sections["Takeaways"]),
      highlights: parseHighlights(sections["Highlights"]),
      topics: Array.isArray(meta.topics) ? meta.topics : [],
    },
  };
}

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

// Fixed key order so comparison is stable regardless of how the JSON was built.
function canonicalHighlight(h) {
  const out = { quote: h.quote, speaker: h.speaker, timestamp: h.timestamp };
  if (h.context !== undefined && h.context !== null) out.context = h.context;
  out.t = h.t ?? timestampToSeconds(h.timestamp);
  return out;
}

const canonicalTakeaway = (t) => ({ title: t.title, detail: t.detail });

function editorialFromRow(row) {
  return {
    one_liner: row.one_liner ?? "",
    summary: (row.summary ?? "").trim(),
    takeaways: JSON.parse(row.takeaways ?? "[]").map(canonicalTakeaway),
    highlights: JSON.parse(row.highlights ?? "[]").map(canonicalHighlight),
    topics: JSON.parse(row.topics ?? "[]"),
  };
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

function selectRows() {
  const where = ["status = 'completed'"];
  const params = [];
  if (onlySlug) {
    where.push("slug = ?");
    params.push(onlySlug);
  }
  return db
    .prepare(`SELECT * FROM ${TABLE} WHERE ${where.join(" AND ")} ORDER BY episode_number`)
    .all(...params);
}

function listDigestFiles() {
  if (!fs.existsSync(DIGESTS_DIR)) return [];
  return fs
    .readdirSync(DIGESTS_DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => path.join(DIGESTS_DIR, f));
}

if (mode === "dump") {
  fs.mkdirSync(DIGESTS_DIR, { recursive: true });
  const rows = selectRows();
  let written = 0;
  let unchanged = 0;
  for (const row of rows) {
    const file = path.join(DIGESTS_DIR, fileNameFor(row));
    const next = renderEpisode(row);
    const prev = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null;
    if (prev === next) {
      unchanged++;
      continue;
    }
    fs.writeFileSync(file, next);
    console.log(`wrote ${path.relative(ROOT, file)}`);
    written++;
  }
  console.log(`dump: ${written} written, ${unchanged} unchanged (${rows.length} completed episodes)`);
}

if (mode === "load") {
  const update = db.prepare(
    `UPDATE ${TABLE}
     SET one_liner = ?, summary = ?, takeaways = ?, highlights = ?, topics = ?, updated_at = ?
     WHERE guid = ?`,
  );
  let updated = 0;
  let unchanged = 0;
  let skipped = 0;
  for (const file of listDigestFiles()) {
    const parsed = parseEpisodeFile(file);
    if (onlySlug && parsed.slug !== onlySlug) continue;
    const row = db.prepare(`SELECT * FROM ${TABLE} WHERE guid = ?`).get(parsed.guid);
    if (!row) {
      console.warn(`skip ${path.basename(file)}: no DB row for guid ${parsed.guid}`);
      skipped++;
      continue;
    }
    if (same(editorialFromRow(row), parsed.fields)) {
      unchanged++;
      continue;
    }
    if (dryRun) {
      console.log(`would update ${parsed.slug}`);
    } else {
      update.run(
        parsed.fields.one_liner,
        parsed.fields.summary,
        JSON.stringify(parsed.fields.takeaways),
        JSON.stringify(parsed.fields.highlights),
        JSON.stringify(parsed.fields.topics),
        Math.floor(Date.now() / 1000),
        parsed.guid,
      );
      console.log(`updated ${parsed.slug}`);
    }
    updated++;
  }
  console.log(
    `load${dryRun ? " (dry-run)" : ""}: ${updated} ${dryRun ? "would change" : "updated"}, ${unchanged} unchanged, ${skipped} skipped`,
  );
}

if (mode === "status") {
  const rows = selectRows();
  const byGuid = new Map(rows.map((r) => [r.guid, r]));
  const seen = new Set();
  for (const file of listDigestFiles()) {
    const parsed = parseEpisodeFile(file);
    seen.add(parsed.guid);
    const row = byGuid.get(parsed.guid);
    if (!row) {
      console.log(`file-only: ${path.basename(file)} (no completed DB row)`);
    } else if (!same(editorialFromRow(row), parsed.fields)) {
      console.log(`differs:   ${parsed.slug}`);
    } else {
      console.log(`in sync:   ${parsed.slug}`);
    }
  }
  for (const row of rows) {
    if (!seen.has(row.guid)) console.log(`db-only:   ${row.slug} (run dump)`);
  }
}

db.close();
