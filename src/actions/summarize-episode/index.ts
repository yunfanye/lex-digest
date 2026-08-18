import {
  createAppLogger,
  defineAction,
  z,
  type Action,
  type ActionConfig,
  type AgentRunnerInterface,
  type AppActionRuntimeDeps,
} from "@rome-os/app-runtime";
import { createEpisodesRepository } from "../../db/repositories/episodes.js";
import {
  fetchTranscript,
  renderTranscriptForPrompt,
  timestampToSeconds,
  type Transcript,
} from "../../lib/feed.js";

const log = createAppLogger("lex_digest_summarize_episode");

const inputSchema = z.object({
  guid: z.string().min(1).describe("Episode guid (primary key in the episodes table)"),
  force: z
    .boolean()
    .optional()
    .describe("Re-summarize even if the episode is already completed or summarizing"),
  requireTranscript: z
    .boolean()
    .optional()
    .describe(
      "Only proceed if the full transcript is fetchable; otherwise skip without touching the episode (used to upgrade show-notes digests once transcripts are published)",
    ),
});

interface DigestPayload {
  one_liner: string;
  summary: string;
  takeaways: { title: string; detail: string }[];
  highlights: { quote: string; speaker: string; timestamp: string; context?: string }[];
  topics: string[];
}

function isDigestPayload(v: unknown): v is DigestPayload {
  if (typeof v !== "object" || v === null) return false;
  const p = v as Record<string, unknown>;
  return (
    typeof p.one_liner === "string" &&
    typeof p.summary === "string" &&
    Array.isArray(p.takeaways) &&
    Array.isArray(p.highlights) &&
    Array.isArray(p.topics)
  );
}

interface Deps {
  agentRunner: AgentRunnerInterface;
}

export function createAction(config: ActionConfig, deps: AppActionRuntimeDeps<Deps>): Action {
  const { appContext, agentRunner } = deps;

  return defineAction({
    config,
    schema: inputSchema,
    execute: async ({ guid, force, requireTranscript }) => {
      const dbCtx = appContext.db;
      if (!dbCtx) return { status: "error", error: "App database is not available" };
      const repo = createEpisodesRepository(dbCtx);

      const episode = repo.byGuid(guid);
      if (!episode) return { status: "error", error: `Unknown episode guid: ${guid}` };
      if (!force && (episode.status === "completed" || episode.status === "summarizing")) {
        return {
          status: "ok",
          data: { guid, skipped: true, reason: `status is ${episode.status}` },
        };
      }

      // 1) Get the source material: transcript preferred, show notes fallback.
      // The transcript URL may be missing from the feed entry even when the
      // transcript page exists, so fall back to the slug-derived canonical URL.
      const transcriptUrl =
        episode.transcriptUrl ?? `https://lexfridman.com/${episode.slug}-transcript/`;
      let transcript: Transcript | null = null;
      try {
        transcript = await fetchTranscript(transcriptUrl);
      } catch (err) {
        log.warn("transcript fetch failed", {
          guid,
          transcriptUrl,
          error: err instanceof Error ? err.message : String(err),
        });
      }

      // Upgrade mode: if the transcript still isn't published, leave the
      // episode exactly as it is (no status churn, no agent run).
      if (requireTranscript && !transcript) {
        return {
          status: "ok",
          data: { guid, skipped: true, reason: "transcript not yet published" },
        };
      }

      repo.update(guid, { status: "summarizing", error: null });
      log.info("summarizing episode", { guid, slug: episode.slug, title: episode.title });

      try {
        const source: "transcript" | "shownotes" = transcript ? "transcript" : "shownotes";
        const material = transcript
          ? renderTranscriptForPrompt(transcript)
          : (episode.shownotes ?? "");

        if (!material.trim()) {
          throw new Error("No transcript and no show notes available to summarize");
        }

        // 2) Run the digester agent with structured output.
        const prompt = [
          `Episode: ${episode.title}`,
          episode.guest ? `Guest: ${episode.guest}` : "",
          `Published: ${episode.pubDate.toISOString().slice(0, 10)}`,
          `Source material: ${source === "transcript" ? "full timestamped transcript" : "show notes only (no transcript published yet — do not invent quotes or timestamps; for highlights, use timestamp \"00:00:00\" and mark context as \"from show notes\")"}`,
          "",
          "--- BEGIN MATERIAL ---",
          material,
          "--- END MATERIAL ---",
          "",
          "Produce the structured digest and submit it via submit_output.",
        ]
          .filter((l) => l !== "")
          .join("\n");

        let digest: DigestPayload | null = null;
        let agentError: string | null = null;
        for await (const msg of agentRunner.run({ agentName: "lex-digester", prompt })) {
          if (msg.type === "structured_output" && isDigestPayload(msg.payload)) {
            digest = msg.payload;
          } else if (msg.type === "error") {
            agentError = typeof msg.error === "string" ? msg.error : "agent error";
          }
        }
        if (!digest) {
          throw new Error(agentError ?? "Digester agent did not submit structured output");
        }

        // 3) Enrich highlights with second offsets for YouTube deep links.
        const highlights = digest.highlights.map((h) => ({
          ...h,
          t: timestampToSeconds(h.timestamp) ?? null,
        }));

        repo.update(guid, {
          status: "completed",
          transcriptUrl: transcript ? transcriptUrl : episode.transcriptUrl,
          summarySource: source,
          error: null,
          oneLiner: digest.one_liner,
          summary: digest.summary,
          takeaways: JSON.stringify(digest.takeaways),
          highlights: JSON.stringify(highlights),
          topics: JSON.stringify(digest.topics),
          youtubeId: transcript?.youtubeId ?? episode.youtubeId,
          chapters: transcript ? JSON.stringify(transcript.chapters) : episode.chapters,
          transcriptChars: transcript?.totalChars ?? episode.transcriptChars,
          segmentCount: transcript?.segments.length ?? episode.segmentCount,
          summarizedAt: new Date(),
        });

        log.info("episode summarized", { guid, source, takeaways: digest.takeaways.length });
        return { status: "ok", data: { guid, slug: episode.slug, source, completed: true } };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        log.error("summarization failed", { guid, error: message });
        repo.update(guid, { status: "failed", error: message });
        return { status: "error", error: `Summarization failed for ${episode.slug}: ${message}` };
      }
    },
  });
}
