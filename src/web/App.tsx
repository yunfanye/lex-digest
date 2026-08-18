import "./styles.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAppApi,
  getCurrentAppPath,
  navigateToApp,
  subscribeToAppPath,
  type RomeAppBootstrap,
} from "@rome-os/app-web-sdk";
import {
  ArrowLeft,
  ExternalLink,
  FileText,
  Headphones,
  ListOrdered,
  Quote,
  RefreshCw,
  Youtube,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@rome-os/ui/alert";
import { Badge } from "@rome-os/ui/badge";
import { Button } from "@rome-os/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@rome-os/ui/card";
import {
  EmptyState,
  EmptyStateDescription,
  EmptyStateTitle,
} from "@rome-os/ui/empty-state";
import { Separator } from "@rome-os/ui/separator";
import { Skeleton } from "@rome-os/ui/skeleton";
import { Spinner } from "@rome-os/ui/spinner";

// ---------- types ----------

interface EpisodeSummary {
  guid: string;
  slug: string;
  episodeNumber: number | null;
  title: string;
  guest: string | null;
  pubDate: string;
  status: "pending" | "summarizing" | "completed" | "failed";
  summarySource: "transcript" | "shownotes" | null;
  oneLiner: string | null;
  topics: string[];
  error: string | null;
}

interface Takeaway {
  title: string;
  detail: string;
}

interface Highlight {
  quote: string;
  speaker: string;
  timestamp: string;
  t: number | null;
  context?: string;
}

interface Chapter {
  title: string;
  timestamp: string | null;
  t: number | null;
}

interface EpisodeDetail extends EpisodeSummary {
  link: string;
  transcriptUrl: string | null;
  audioUrl: string | null;
  youtubeId: string | null;
  summary: string | null;
  takeaways: Takeaway[];
  highlights: Highlight[];
  chapters: Chapter[];
  transcriptChars: number | null;
  segmentCount: number | null;
  summarizedAt: string | null;
}

interface AppState {
  podcastArt: string;
  episodes: EpisodeSummary[];
  lastCheck: { ranAt: string; status: string; newCount: number | null; note: string | null } | null;
}

// ---------- helpers ----------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function youtubeAt(youtubeId: string | null, t: number | null): string | null {
  if (!youtubeId) return null;
  return `https://youtube.com/watch?v=${youtubeId}${t ? `&t=${t}` : ""}`;
}

function StatusBadge({ status }: { status: EpisodeSummary["status"] }) {
  if (status === "completed") return null;
  if (status === "summarizing") {
    return (
      <Badge variant="brand" className="gap-1.5">
        <Spinner size="sm" label="Summarizing" /> Digesting
      </Badge>
    );
  }
  if (status === "pending") return <Badge variant="muted">Queued</Badge>;
  return <Badge variant="destructive">Failed</Badge>;
}

const hasWorkInFlight = (eps: EpisodeSummary[]) =>
  eps.some((e) => e.status === "pending" || e.status === "summarizing");

// ---------- list view ----------

function EpisodeListItem({ ep }: { ep: EpisodeSummary }) {
  return (
    <button
      type="button"
      onClick={() => navigateToApp(ep.slug)}
      className="w-full rounded-lg border border-border bg-card p-4 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-5"
    >
      <div className="flex flex-wrap items-center gap-2">
        {ep.episodeNumber !== null && <Badge variant="outline">#{ep.episodeNumber}</Badge>}
        <span className="text-sm text-muted-foreground">{formatDate(ep.pubDate)}</span>
        <StatusBadge status={ep.status} />
      </div>
      <h2 className="mt-2 text-base font-semibold leading-snug sm:text-lg">{ep.title}</h2>
      {ep.oneLiner ? (
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{ep.oneLiner}</p>
      ) : ep.status === "failed" && ep.error ? (
        <p className="mt-1.5 text-sm text-destructive">{ep.error}</p>
      ) : null}
      {ep.topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {ep.topics.map((t) => (
            <Badge key={t} variant="muted" className="font-normal">
              {t}
            </Badge>
          ))}
        </div>
      )}
    </button>
  );
}

function ListView({
  state,
  loading,
  error,
  onCheck,
  checking,
}: {
  state: AppState | null;
  loading: boolean;
  error: string | null;
  onCheck: () => void;
  checking: boolean;
}) {
  const episodes = state?.episodes ?? [];
  const busy = checking || (state !== null && hasWorkInFlight(episodes));

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {state?.podcastArt ? (
          <img
            src={state.podcastArt}
            alt="Lex Fridman Podcast artwork"
            className="h-16 w-16 rounded-lg border border-border object-cover"
          />
        ) : (
          <Skeleton className="h-16 w-16 rounded-lg" />
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Lex Digest</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Lex Fridman Podcast · transcript summaries, takeaways &amp; highlights · checked every
            2 hours
          </p>
          {state?.lastCheck && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              Last checked {timeAgo(state.lastCheck.ranAt)}
              {episodes.length > 0 && <> · {episodes.length} episodes</>}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={onCheck} disabled={busy}>
          {busy ? <Spinner size="sm" label="Checking feed" /> : <RefreshCw />}
          {busy ? "Working…" : "Check feed"}
        </Button>
      </header>

      {error && (
        <Alert variant="destructive" className="mt-6">
          <AlertTitle>Could not load episodes</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mt-6 flex flex-col gap-3">
        {loading && !state ? (
          <>
            <Skeleton className="h-32 w-full rounded-lg" />
            <Skeleton className="h-32 w-full rounded-lg" />
            <Skeleton className="h-32 w-full rounded-lg" />
          </>
        ) : episodes.length === 0 ? (
          <EmptyState>
            <EmptyStateTitle>No episodes yet</EmptyStateTitle>
            <EmptyStateDescription>
              Run a feed check to pull in the latest episodes and generate their digests.
            </EmptyStateDescription>
          </EmptyState>
        ) : (
          episodes.map((ep) => <EpisodeListItem key={ep.guid} ep={ep} />)
        )}
      </div>
    </div>
  );
}

// ---------- detail view ----------

function ExternalLinkButton({
  href,
  icon,
  label,
}: {
  href: string | null;
  icon: React.ReactNode;
  label: string;
}) {
  if (!href) return null;
  return (
    <Button variant="outline" size="sm" asChild>
      <a href={href} target="_blank" rel="noreferrer">
        {icon}
        {label}
        <ExternalLink className="opacity-60" />
      </a>
    </Button>
  );
}

function DetailView({ slug }: { slug: string }) {
  const [episode, setEpisode] = useState<EpisodeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetchAppApi(`episodes/${encodeURIComponent(slug)}`);
      if (!res.ok) throw new Error(res.status === 404 ? "Episode not found" : `HTTP ${res.status}`);
      const data = (await res.json()) as { episode: EpisodeDetail };
      setEpisode(data.episode);
      setError(null);
      return data.episode;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll while a digest is being generated for this episode.
  useEffect(() => {
    if (!episode || (episode.status !== "pending" && episode.status !== "summarizing")) return;
    const id = setInterval(() => void load(), 5000);
    return () => clearInterval(id);
  }, [episode, load]);

  const retry = useCallback(async () => {
    setRetrying(true);
    try {
      await fetchAppApi(`episodes/${encodeURIComponent(slug)}/summarize`, { method: "POST" });
      await load();
    } finally {
      setRetrying(false);
    }
  }, [slug, load]);

  if (error) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
        <BackLink />
        <Alert variant="destructive" className="mt-6">
          <AlertTitle>Could not load episode</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!episode) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
        <BackLink />
        <Skeleton className="mt-6 h-8 w-3/4" />
        <Skeleton className="mt-3 h-4 w-1/2" />
        <Skeleton className="mt-6 h-48 w-full rounded-lg" />
      </div>
    );
  }

  const paragraphs = (episode.summary ?? "")
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <BackLink />

      <header className="mt-5">
        <div className="flex flex-wrap items-center gap-2">
          {episode.episodeNumber !== null && (
            <Badge variant="outline">#{episode.episodeNumber}</Badge>
          )}
          <span className="text-sm text-muted-foreground">{formatDate(episode.pubDate)}</span>
          {episode.summarySource === "transcript" && (
            <Badge variant="muted">From full transcript</Badge>
          )}
          {episode.summarySource === "shownotes" && (
            <Badge variant="warning">From show notes — transcript not published yet</Badge>
          )}
          <StatusBadge status={episode.status} />
        </div>
        <h1 className="mt-2 text-xl font-semibold leading-snug tracking-tight sm:text-2xl">
          {episode.title}
        </h1>
        {episode.oneLiner && (
          <p className="mt-2 text-base leading-relaxed text-muted-foreground">{episode.oneLiner}</p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <ExternalLinkButton
            href={youtubeAt(episode.youtubeId, null)}
            icon={<Youtube />}
            label="Watch"
          />
          <ExternalLinkButton href={episode.audioUrl} icon={<Headphones />} label="Listen" />
          <ExternalLinkButton
            href={episode.transcriptUrl}
            icon={<FileText />}
            label="Transcript"
          />
        </div>
      </header>

      {episode.status === "failed" && (
        <Alert variant="destructive" className="mt-6">
          <AlertTitle>Digest failed</AlertTitle>
          <AlertDescription className="flex flex-col gap-3">
            <span>{episode.error ?? "Unknown error"}</span>
            <Button variant="outline" size="sm" onClick={retry} disabled={retrying} className="w-fit">
              {retrying ? <Spinner size="sm" label="Retrying" /> : <RefreshCw />}
              Retry digest
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {(episode.status === "pending" || episode.status === "summarizing") && (
        <Card className="mt-6">
          <CardContent className="flex items-center gap-3 py-6 text-sm text-muted-foreground">
            <Spinner label="Digesting" />
            {episode.status === "summarizing"
              ? "Reading the transcript and writing the digest — this takes a few minutes."
              : "Queued for digestion."}
          </CardContent>
        </Card>
      )}

      {paragraphs.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Summary
          </h2>
          <div className="mt-3 flex flex-col gap-4">
            {paragraphs.map((p, i) => (
              <p key={i} className="text-base leading-relaxed">
                {p}
              </p>
            ))}
          </div>
        </section>
      )}

      {episode.takeaways.length > 0 && (
        <section className="mt-8">
          <h2 className="flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-muted-foreground">
            <ListOrdered className="h-4 w-4" /> Key takeaways
          </h2>
          <div className="mt-3 flex flex-col gap-3">
            {episode.takeaways.map((t, i) => (
              <div key={i} className="flex gap-3 rounded-lg border border-border bg-card p-4">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <div>
                  <p className="font-medium leading-snug">{t.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{t.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {episode.highlights.length > 0 && (
        <section className="mt-8">
          <h2 className="flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-muted-foreground">
            <Quote className="h-4 w-4" /> Highlights
          </h2>
          <div className="mt-3 flex flex-col gap-3">
            {episode.highlights.map((h, i) => {
              const link = youtubeAt(episode.youtubeId, h.t);
              return (
                <figure key={i} className="rounded-lg border border-border bg-card p-4">
                  <blockquote className="border-l-2 border-primary pl-3 text-base leading-relaxed">
                    “{h.quote}”
                  </blockquote>
                  <figcaption className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 pl-3 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{h.speaker}</span>
                    {link ? (
                      <a
                        href={link}
                        target="_blank"
                        rel="noreferrer"
                        className="tabular-nums underline decoration-border underline-offset-2 hover:text-foreground"
                      >
                        {h.timestamp}
                      </a>
                    ) : (
                      <span className="tabular-nums">{h.timestamp}</span>
                    )}
                    {h.context && <span>· {h.context}</span>}
                  </figcaption>
                </figure>
              );
            })}
          </div>
        </section>
      )}

      {episode.chapters.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Chapters
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {episode.chapters.map((c, i) => {
              const link = youtubeAt(episode.youtubeId, c.t);
              return (
                <div key={i} className="flex items-baseline gap-2 text-sm">
                  {link ? (
                    <a
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      className="shrink-0 tabular-nums text-muted-foreground underline decoration-border underline-offset-2 hover:text-foreground"
                    >
                      {c.timestamp ?? "—"}
                    </a>
                  ) : (
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {c.timestamp ?? "—"}
                    </span>
                  )}
                  <span className="leading-snug">{c.title}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {episode.topics.length > 0 && (
        <>
          <Separator className="mt-8" />
          <div className="mt-4 flex flex-wrap gap-1.5 pb-8">
            {episode.topics.map((t) => (
              <Badge key={t} variant="muted" className="font-normal">
                {t}
              </Badge>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Button variant="ghost" size="sm" onClick={() => navigateToApp("")} className="-ml-2">
      <ArrowLeft /> All episodes
    </Button>
  );
}

// ---------- root ----------

export default function App({ bootstrap: _bootstrap }: { bootstrap: RomeAppBootstrap }) {
  const [path, setPath] = useState<string>(() => getCurrentAppPath());
  const [state, setState] = useState<AppState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => subscribeToAppPath(setPath), []);

  const loadState = useCallback(async () => {
    try {
      const res = await fetchAppApi("state");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as AppState;
      setState(data);
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  // Poll only while a check or digest is in flight.
  useEffect(() => {
    const active = checking || (state !== null && hasWorkInFlight(state.episodes));
    if (active && pollRef.current === null) {
      pollRef.current = setInterval(() => void loadState(), 5000);
    }
    if (!active && pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current !== null) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [checking, state, loadState]);

  const onCheck = useCallback(async () => {
    setChecking(true);
    try {
      await fetchAppApi("check", { method: "POST" });
      // Give the detached run a moment to mark episodes, then resume polling.
      setTimeout(() => {
        void loadState();
        setChecking(false);
      }, 3000);
    } catch {
      setChecking(false);
    }
  }, [loadState]);

  const view = useMemo(() => {
    const slug = path.replace(/^\/+|\/+$/g, "");
    if (slug) return <DetailView slug={slug} />;
    return (
      <ListView
        state={state}
        loading={loading}
        error={error}
        onCheck={onCheck}
        checking={checking}
      />
    );
  }, [path, state, loading, error, onCheck, checking]);

  return <main className="min-h-full bg-background text-foreground">{view}</main>;
}
