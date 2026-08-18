import type { RomeAppApiHandler, RomeAppApiRequest, RomeAppContext } from "@rome-os/app-runtime";
import { createEpisodesRepository, type EpisodeRow } from "../db/repositories/episodes.js";
import { PODCAST_ART_URL } from "../lib/feed.js";

function json(data: unknown, init?: ResponseInit): Response {
  return Response.json(data, init);
}

function parseJson<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function episodeSummary(row: EpisodeRow) {
  return {
    guid: row.guid,
    slug: row.slug,
    episodeNumber: row.episodeNumber,
    title: row.title,
    guest: row.guest,
    pubDate: row.pubDate.toISOString(),
    status: row.status,
    summarySource: row.summarySource,
    oneLiner: row.oneLiner,
    topics: parseJson<string[]>(row.topics, []),
    error: row.error,
  };
}

function episodeDetail(row: EpisodeRow) {
  return {
    ...episodeSummary(row),
    link: row.link,
    transcriptUrl: row.transcriptUrl,
    audioUrl: row.audioUrl,
    youtubeId: row.youtubeId,
    summary: row.summary,
    takeaways: parseJson<{ title: string; detail: string }[]>(row.takeaways, []),
    highlights: parseJson<
      { quote: string; speaker: string; timestamp: string; t: number | null; context?: string }[]
    >(row.highlights, []),
    chapters: parseJson<{ title: string; timestamp: string | null; t: number | null }[]>(
      row.chapters,
      [],
    ),
    transcriptChars: row.transcriptChars,
    segmentCount: row.segmentCount,
    summarizedAt: row.summarizedAt ? row.summarizedAt.toISOString() : null,
  };
}

class LexDigestApiHandler implements RomeAppApiHandler {
  constructor(private readonly ctx: RomeAppContext) {}

  private repo() {
    const dbCtx = this.ctx.db;
    if (!dbCtx) throw new Error("App database is not available");
    return createEpisodesRepository(dbCtx);
  }

  async handle(request: RomeAppApiRequest): Promise<Response> {
    const route = request.path.join("/");

    if (request.method === "GET" && route === "state") {
      const repo = this.repo();
      const last = repo.lastCheck();
      return json({
        podcastArt: PODCAST_ART_URL,
        episodes: repo.list().map(episodeSummary),
        lastCheck: last
          ? {
              ranAt: last.ranAt.toISOString(),
              status: last.status,
              newCount: last.newCount,
              note: last.note,
            }
          : null,
      });
    }

    if (request.method === "GET" && request.path[0] === "episodes" && request.path.length === 2) {
      const row = this.repo().bySlug(request.path[1]);
      if (!row) return json({ error: "not_found" }, { status: 404 });
      return json({ episode: episodeDetail(row) });
    }

    // Writes below are guardian-only.
    if (request.method === "POST") {
      if (request.caller.kind !== "guardian") {
        return json({ error: "forbidden" }, { status: 401 });
      }

      if (route === "check") {
        // Long-running (fetch + agent runs) — detach so the HTTP request
        // returns immediately; the UI polls /state for progress.
        let args: Record<string, unknown> = {};
        if (request.body && request.body.byteLength > 0) {
          try {
            const parsed = JSON.parse(new TextDecoder().decode(request.body)) as {
              maxNew?: number;
              scanLimit?: number;
            };
            if (typeof parsed.maxNew === "number") args.maxNew = parsed.maxNew;
            if (typeof parsed.scanLimit === "number") args.scanLimit = parsed.scanLimit;
          } catch {
            return json({ error: "invalid_json" }, { status: 400 });
          }
        }
        const receipt = await this.ctx.runAction("lex_digest_check_feed", args, {
          detached: true,
        });
        return json({ started: true, receipt }, { status: 202 });
      }

      if (request.path[0] === "episodes" && request.path.length === 3 && request.path[2] === "summarize") {
        const repo = this.repo();
        const row = repo.bySlug(request.path[1]);
        if (!row) return json({ error: "not_found" }, { status: 404 });
        repo.update(row.guid, { status: "pending", error: null });
        const receipt = await this.ctx.runAction(
          "lex_digest_summarize_episode",
          { guid: row.guid, force: true },
          { detached: true },
        );
        return json({ started: true, receipt }, { status: 202 });
      }
    }

    return json({ error: "not_found", message: `Unknown route: /${route}` }, { status: 404 });
  }
}

export function createApiHandler(ctx: RomeAppContext): RomeAppApiHandler {
  return new LexDigestApiHandler(ctx);
}
