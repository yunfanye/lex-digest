import {
  createAppLogger,
  defineAction,
  z,
  type Action,
  type ActionConfig,
  type AppActionRuntimeDeps,
} from "@rome-os/app-runtime";
import { createEpisodesRepository } from "../../db/repositories/episodes.js";
import { fetchFeed } from "../../lib/feed.js";

const log = createAppLogger("lex_digest_check_feed");

const inputSchema = z.object({
  maxNew: z
    .number()
    .int()
    .min(1)
    .max(20)
    .optional()
    .describe("Maximum number of new episodes to ingest in one run (default 3; use 5 for backfill)"),
  scanLimit: z
    .number()
    .int()
    .min(1)
    .max(50)
    .optional()
    .describe("How many feed items to scan (default 12)"),
  retryFailed: z
    .boolean()
    .optional()
    .describe("Also retry episodes whose last summarization failed (default true)"),
});

export function createAction(config: ActionConfig, deps: AppActionRuntimeDeps): Action {
  const { appContext } = deps;

  return defineAction({
    config,
    schema: inputSchema,
    execute: async ({ maxNew = 3, scanLimit = 12, retryFailed = true }) => {
      const dbCtx = appContext.db;
      if (!dbCtx) return { status: "error", error: "App database is not available" };
      const repo = createEpisodesRepository(dbCtx);
      const ranAt = new Date();

      try {
        const feed = await fetchFeed(scanLimit);
        const newestStored = repo.newestPubDate();

        // Genuinely new = not stored yet AND (no history yet, or newer than
        // what we have — so a first backfill doesn't make every older feed
        // item look "new" on later runs).
        const candidates = feed
          .filter((ep) => !repo.byGuid(ep.guid))
          .filter((ep) => newestStored === null || ep.pubDate > newestStored)
          .slice(0, maxNew)
          .reverse(); // oldest first so the list fills chronologically

        const now = new Date();
        for (const ep of candidates) {
          repo.insert({
            guid: ep.guid,
            slug: ep.slug,
            episodeNumber: ep.episodeNumber,
            title: ep.title,
            guest: ep.guest,
            link: ep.link,
            transcriptUrl: ep.transcriptUrl,
            audioUrl: ep.audioUrl,
            pubDate: ep.pubDate,
            shownotes: ep.shownotes,
            status: "pending",
            createdAt: now,
            updatedAt: now,
          });
          log.info("new episode stored", { guid: ep.guid, title: ep.title });
        }

        // Work queue: freshly inserted episodes, any stragglers still pending,
        // and (optionally) failed ones worth retrying.
        const queue = repo
          .list()
          .filter((e) => e.status === "pending" || (retryFailed && e.status === "failed"))
          .sort((a, b) => a.pubDate.getTime() - b.pubDate.getTime());

        let summarized = 0;
        const failures: string[] = [];
        for (const ep of queue) {
          const result = await appContext.runAction("lex_digest_summarize_episode", {
            guid: ep.guid,
            force: ep.status === "failed",
          });
          if (result.status === "ok") summarized++;
          else if (result.status === "error") failures.push(result.error);
        }

        // Upgrade pass: episodes digested from show notes get re-digested
        // from the full transcript once it's published. requireTranscript
        // makes this a cheap no-op (one HTTP probe) until then.
        let upgraded = 0;
        const upgradeCandidates = repo
          .list()
          .filter((e) => e.status === "completed" && e.summarySource === "shownotes");
        for (const ep of upgradeCandidates) {
          const result = await appContext.runAction("lex_digest_summarize_episode", {
            guid: ep.guid,
            force: true,
            requireTranscript: true,
          });
          if (
            result.status === "ok" &&
            typeof result.data === "object" &&
            result.data !== null &&
            (result.data as { completed?: boolean }).completed
          ) {
            upgraded++;
          } else if (result.status === "error") {
            failures.push(result.error);
          }
        }

        repo.recordCheck({
          ranAt,
          status: failures.length > 0 ? "error" : "ok",
          feedCount: feed.length,
          newCount: candidates.length,
          summarizedCount: summarized + upgraded,
          note:
            failures.length > 0
              ? failures.join(" | ").slice(0, 500)
              : upgraded > 0
                ? `upgraded ${upgraded} digest(s) to transcript`
                : null,
        });

        log.info("feed check complete", {
          feedCount: feed.length,
          newCount: candidates.length,
          summarized,
          upgraded,
          failures: failures.length,
        });
        return {
          status: "ok",
          data: {
            feedCount: feed.length,
            newEpisodes: candidates.map((e) => e.title),
            summarized,
            upgraded,
            failures,
          },
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        log.error("feed check failed", { error: message });
        repo.recordCheck({
          ranAt,
          status: "error",
          feedCount: null,
          newCount: null,
          summarizedCount: null,
          note: message.slice(0, 500),
        });
        return { status: "error", error: `Feed check failed: ${message}` };
      }
    },
  });
}
