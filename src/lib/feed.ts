/**
 * Fetching + parsing for the Lex Fridman Podcast RSS feed and the
 * transcript pages on lexfridman.com. No external XML/HTML dependencies —
 * the feed shape is stable (WordPress/PowerPress) and parsing is scoped
 * to the handful of fields we need.
 */

export const FEED_URL = "https://lexfridman.com/feed/podcast/";
export const PODCAST_ART_URL =
  "https://lexfridman.com/wordpress/wp-content/uploads/powerpress/artwork_3000-230.png";

const FETCH_HEADERS = {
  "user-agent":
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 RomeLexDigest/1.0",
  accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
};

export interface FeedEpisode {
  guid: string;
  slug: string;
  episodeNumber: number | null;
  title: string;
  guest: string | null;
  link: string;
  transcriptUrl: string | null;
  audioUrl: string | null;
  pubDate: Date;
  shownotes: string;
}

export interface TranscriptSegment {
  speaker: string;
  timestamp: string; // "HH:MM:SS"
  t: number; // seconds
  text: string;
  chapter: string | null;
}

export interface TranscriptChapter {
  title: string;
  timestamp: string | null;
  t: number | null;
}

export interface Transcript {
  youtubeId: string | null;
  chapters: TranscriptChapter[];
  segments: TranscriptSegment[];
  totalChars: number;
}

const NAMED_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
  hellip: "…",
  mdash: "—",
  ndash: "–",
  rsquo: "\u2019",
  lsquo: "\u2018",
  rdquo: "\u201d",
  ldquo: "\u201c",
};

export function decodeEntities(input: string): string {
  return input
    .replace(/&#(\d+);/g, (_, d: string) => String.fromCodePoint(Number(d)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h: string) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&([a-zA-Z]+);/g, (m, name: string) => NAMED_ENTITIES[name] ?? m);
}

function stripTags(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<[^>]+>/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function tagContent(block: string, tag: string): string | null {
  const m = block.match(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)</${tag}>`, "i"));
  return m ? m[1].trim() : null;
}

export function timestampToSeconds(ts: string): number | null {
  const m = ts.trim().match(/^\(?(?:(\d+):)?(\d{1,2}):(\d{2})\)?$/);
  if (!m) return null;
  const h = m[1] ? Number(m[1]) : 0;
  return h * 3600 + Number(m[2]) * 60 + Number(m[3]);
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url, { headers: FETCH_HEADERS, redirect: "follow" });
  if (!res.ok) {
    throw new Error(`Fetch failed (${res.status}) for ${url}`);
  }
  return await res.text();
}

/** Parse the RSS feed. Returns episodes newest-first (feed order). */
export async function fetchFeed(limit = 15): Promise<FeedEpisode[]> {
  const xml = await fetchText(FEED_URL);
  const items = xml.match(/<item>[\s\S]*?<\/item>/g) ?? [];
  const episodes: FeedEpisode[] = [];

  for (const item of items.slice(0, limit)) {
    const rawGuid = tagContent(item, "guid");
    const rawTitle = tagContent(item, "title");
    const rawLink = tagContent(item, "link");
    const rawPubDate = tagContent(item, "pubDate");
    if (!rawGuid || !rawTitle || !rawLink || !rawPubDate) continue;

    const pubDate = new Date(rawPubDate);
    if (Number.isNaN(pubDate.getTime())) continue;

    const title = decodeEntities(rawTitle).trim();
    const link = decodeEntities(rawLink).trim();
    const url = new URL(link);
    const slug = url.pathname.replace(/\/+$/g, "").split("/").pop() ?? rawGuid;

    const numMatch = title.match(/^#(\d+)/);
    const episodeNumber = numMatch ? Number(numMatch[1]) : null;
    // "#500 – Guest Name: Topic, Topic" → guest = "Guest Name"
    const guestMatch = title.match(/^#\d+\s*[–—-]\s*([^:]+):/);
    const guest = guestMatch ? guestMatch[1].trim() : null;

    const rawDesc = tagContent(item, "description") ?? "";
    const descHtml = decodeEntities(rawDesc);
    const transcriptMatch = descHtml.match(
      /https:\/\/lexfridman\.com\/[a-z0-9-]+-transcript\/?/i,
    );
    const enclosureMatch = item.match(/<enclosure\s[^>]*url="([^"]+)"/i);

    episodes.push({
      guid: decodeEntities(rawGuid).trim(),
      slug,
      episodeNumber,
      title,
      guest,
      link: `${url.origin}${url.pathname}`,
      transcriptUrl: transcriptMatch ? transcriptMatch[0].replace(/\/?$/, "/") : null,
      audioUrl: enclosureMatch ? decodeEntities(enclosureMatch[1]) : null,
      pubDate,
      shownotes: trimShownotes(stripTags(decodeEntities(stripCdata(rawDesc)))),
    });
  }

  return episodes;
}

function stripCdata(s: string): string {
  return s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1");
}

/**
 * The feed description mixes an actual episode intro with boilerplate
 * (sponsors, contact links, socials). Keep the intro paragraphs, drop
 * everything from the boilerplate headers on.
 */
function trimShownotes(text: string): string {
  const cutMarkers = [
    "Thank you for listening",
    "CONTACT LEX:",
    "EPISODE LINKS:",
    "Transcript:",
    "SPONSORS:",
  ];
  let cut = text.length;
  for (const marker of cutMarkers) {
    const i = text.indexOf(marker);
    if (i !== -1 && i < cut) cut = i;
  }
  return text.slice(0, cut).trim();
}

/** Parse a lexfridman.com transcript page into chapters + timestamped segments. */
export async function fetchTranscript(transcriptUrl: string): Promise<Transcript> {
  const html = await fetchText(transcriptUrl);

  const ytMatch =
    html.match(/youtube\.com\/embed\/([\w-]{6,})/) ??
    html.match(/youtube\.com\/watch\?v=([\w-]{6,})/);
  const youtubeId = ytMatch ? ytMatch[1] : null;

  // Walk chapters (<h2 id="chapterN_..."><span id="...">Title</span></h2>)
  // and segments (<div class="ts-segment">…) in document order so each
  // segment knows its chapter.
  const tokenRe =
    /<h2 id="chapter\d+_[^"]*">\s*<span id="[^"]*">([^<]*)<\/span>\s*<\/h2>|<div class="ts-segment">\s*<span class="ts-name">([\s\S]*?)<\/span>\s*<span class="ts-timestamp">([\s\S]*?)<\/span>\s*<span class="ts-text">([\s\S]*?)<\/span>/g;

  const chapters: TranscriptChapter[] = [];
  const segments: TranscriptSegment[] = [];
  let currentChapter: TranscriptChapter | null = null;
  let match: RegExpExecArray | null;

  while ((match = tokenRe.exec(html)) !== null) {
    if (match[1] !== undefined) {
      currentChapter = { title: decodeEntities(match[1]).trim(), timestamp: null, t: null };
      chapters.push(currentChapter);
      continue;
    }
    const speaker = decodeEntities(stripTags(match[2])).trim();
    const tsRaw = stripTags(match[3]).trim(); // "(00:12:34)"
    const tsClean = tsRaw.replace(/[()]/g, "");
    const t = timestampToSeconds(tsClean);
    const text = decodeEntities(stripTags(match[4])).trim();
    if (!text) continue;
    if (currentChapter && currentChapter.timestamp === null) {
      currentChapter.timestamp = tsClean;
      currentChapter.t = t;
    }
    segments.push({
      speaker,
      timestamp: tsClean,
      t: t ?? 0,
      text,
      chapter: currentChapter?.title ?? null,
    });
  }

  const totalChars = segments.reduce((sum, s) => sum + s.text.length, 0);
  if (segments.length === 0) {
    throw new Error(`No transcript segments found at ${transcriptUrl}`);
  }
  return { youtubeId, chapters, segments, totalChars };
}

/**
 * Render the transcript as plain text lines for the summarizer prompt.
 * If it exceeds `maxChars`, keep the head and tail and drop the middle
 * with an explicit marker (episodes run 1–5 hours; most fit whole).
 */
export function renderTranscriptForPrompt(transcript: Transcript, maxChars = 300_000): string {
  const lines: string[] = [];
  let lastChapter: string | null = null;
  for (const seg of transcript.segments) {
    if (seg.chapter !== lastChapter && seg.chapter) {
      lines.push(`\n## ${seg.chapter}\n`);
      lastChapter = seg.chapter;
    }
    lines.push(`(${seg.timestamp}) ${seg.speaker}: ${seg.text}`);
  }
  const full = lines.join("\n");
  if (full.length <= maxChars) return full;

  const headBudget = Math.floor(maxChars * 0.7);
  const tailBudget = Math.floor(maxChars * 0.25);
  let head = "";
  let i = 0;
  while (i < lines.length && head.length + lines[i].length + 1 <= headBudget) {
    head += lines[i] + "\n";
    i++;
  }
  let tail = "";
  let j = lines.length - 1;
  while (j > i && tail.length + lines[j].length + 1 <= tailBudget) {
    tail = lines[j] + "\n" + tail;
    j--;
  }
  return `${head}\n[... middle of transcript trimmed for length ...]\n\n${tail}`;
}
