import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export function createAppDbSchema(tablePrefix: string = "lex_digest") {
  const episodes = sqliteTable(`${tablePrefix}__episodes`, {
    guid: text("guid").primaryKey(),
    slug: text("slug").notNull(),
    episodeNumber: integer("episode_number"),
    title: text("title").notNull(),
    guest: text("guest"),
    link: text("link").notNull(),
    transcriptUrl: text("transcript_url"),
    audioUrl: text("audio_url"),
    youtubeId: text("youtube_id"),
    pubDate: integer("pub_date", { mode: "timestamp" }).notNull(),
    shownotes: text("shownotes"),
    chapters: text("chapters"), // JSON [{ title, timestamp, t }]
    status: text("status").notNull().default("pending"), // pending | summarizing | completed | failed
    summarySource: text("summary_source"), // transcript | shownotes
    error: text("error"),
    oneLiner: text("one_liner"),
    summary: text("summary"), // paragraphs separated by blank lines
    takeaways: text("takeaways"), // JSON [{ title, detail }]
    highlights: text("highlights"), // JSON [{ quote, speaker, timestamp, t, context }]
    topics: text("topics"), // JSON [string]
    transcriptChars: integer("transcript_chars"),
    segmentCount: integer("segment_count"),
    createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull(),
    summarizedAt: integer("summarized_at", { mode: "timestamp" }),
  });

  const checks = sqliteTable(`${tablePrefix}__checks`, {
    id: text("id").primaryKey(),
    ranAt: integer("ran_at", { mode: "timestamp" }).notNull(),
    status: text("status").notNull(), // ok | error
    feedCount: integer("feed_count"),
    newCount: integer("new_count"),
    summarizedCount: integer("summarized_count"),
    note: text("note"),
  });

  return { episodes, checks };
}

const defaultSchema = createAppDbSchema();

export const episodes = defaultSchema.episodes;
export const checks = defaultSchema.checks;
