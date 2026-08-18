import { desc, eq } from "drizzle-orm";
import type { AppDbContext, DrizzleDb } from "@rome-os/app-runtime";
import { createAppDbSchema } from "../schema.js";

export type EpisodeStatus = "pending" | "summarizing" | "completed" | "failed";

export interface EpisodeRow {
  guid: string;
  slug: string;
  episodeNumber: number | null;
  title: string;
  guest: string | null;
  link: string;
  transcriptUrl: string | null;
  audioUrl: string | null;
  youtubeId: string | null;
  pubDate: Date;
  shownotes: string | null;
  chapters: string | null;
  status: string;
  summarySource: string | null;
  error: string | null;
  oneLiner: string | null;
  summary: string | null;
  takeaways: string | null;
  highlights: string | null;
  topics: string | null;
  transcriptChars: number | null;
  segmentCount: number | null;
  createdAt: Date;
  updatedAt: Date;
  summarizedAt: Date | null;
}

export interface CheckRow {
  id: string;
  ranAt: Date;
  status: string;
  feedCount: number | null;
  newCount: number | null;
  summarizedCount: number | null;
  note: string | null;
}

export class EpisodesRepository {
  private readonly tables;

  constructor(
    private readonly db: DrizzleDb,
    tablePrefix: string,
  ) {
    this.tables = createAppDbSchema(tablePrefix);
  }

  list(): EpisodeRow[] {
    return this.db
      .select()
      .from(this.tables.episodes)
      .orderBy(desc(this.tables.episodes.pubDate))
      .all() as EpisodeRow[];
  }

  byGuid(guid: string): EpisodeRow | undefined {
    return this.db
      .select()
      .from(this.tables.episodes)
      .where(eq(this.tables.episodes.guid, guid))
      .get() as EpisodeRow | undefined;
  }

  bySlug(slug: string): EpisodeRow | undefined {
    return this.db
      .select()
      .from(this.tables.episodes)
      .where(eq(this.tables.episodes.slug, slug))
      .get() as EpisodeRow | undefined;
  }

  newestPubDate(): Date | null {
    const row = this.db
      .select({ pubDate: this.tables.episodes.pubDate })
      .from(this.tables.episodes)
      .orderBy(desc(this.tables.episodes.pubDate))
      .limit(1)
      .get();
    return row?.pubDate ?? null;
  }

  insert(row: typeof this.tables.episodes.$inferInsert): void {
    this.db.insert(this.tables.episodes).values(row).run();
  }

  update(guid: string, patch: Partial<typeof this.tables.episodes.$inferInsert>): void {
    this.db
      .update(this.tables.episodes)
      .set({ ...patch, updatedAt: new Date() })
      .where(eq(this.tables.episodes.guid, guid))
      .run();
  }

  recordCheck(row: Omit<CheckRow, "id">): void {
    this.db
      .insert(this.tables.checks)
      .values({ id: crypto.randomUUID(), ...row })
      .run();
  }

  lastCheck(): CheckRow | undefined {
    return this.db
      .select()
      .from(this.tables.checks)
      .orderBy(desc(this.tables.checks.ranAt))
      .limit(1)
      .get() as CheckRow | undefined;
  }
}

export function createEpisodesRepository(ctx: AppDbContext): EpisodesRepository {
  return new EpisodesRepository(ctx.connection, ctx.tablePrefix);
}
