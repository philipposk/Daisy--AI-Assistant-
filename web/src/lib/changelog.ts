import { readFile } from "node:fs/promises";
import path from "node:path";

export type ChangelogEntry = {
  version: string;        // "1.5"
  title: string;          // "Stable release"  (may be empty)
  date: string;           // "2026-05-26"     (may be empty)
  userSummary: string;    // raw markdown for "What this gives you" block
  technicalDetails: string; // raw markdown for "Technical details" block (may be empty)
};

// Synced copy of `Daisy -AI Assistant- 1.5/CHANGELOG.md`. Vercel only uploads
// `web/`, so the source-of-truth file outside this dir is not visible at build
// time. Re-copy after future Daisy releases (or wire a prebuild script).
const CHANGELOG_PATH = path.resolve(process.cwd(), "src", "content", "CHANGELOG.md");

/**
 * Parse the Daisy CHANGELOG.md file into structured version entries.
 *
 * The format is stable:
 *   ## X.Y [— title] (date)
 *   **What this gives you:**
 *   <prose paragraph>
 *   **Technical details[ (N fixes)]:**
 *   - bullet
 *   - bullet
 *
 * Versions are separated by `---`. The newest version comes first.
 */
export async function readChangelog(): Promise<ChangelogEntry[]> {
  const raw = await readFile(CHANGELOG_PATH, "utf8");
  const sections = raw.split(/\n---\n/);
  const entries: ChangelogEntry[] = [];

  for (const section of sections) {
    const headerMatch = section.match(/^##\s+([0-9]+\.[0-9]+)\s*(?:—\s*([^()]+?)\s*)?(?:\(([^)]+)\))?\s*$/m);
    if (!headerMatch) continue;

    const version = headerMatch[1];
    const title = (headerMatch[2] ?? "").trim();
    const date = (headerMatch[3] ?? "").trim();

    const userBlock = section.match(
      /\*\*What this (?:gives|gave) you:\*\*\s*\n([\s\S]*?)(?=\n\*\*Technical details[\s\S]*?\*\*|\n##|$)/,
    );
    const techBlock = section.match(
      /\*\*Technical details[^*]*\*\*\s*\n([\s\S]*?)(?=\n##|$)/,
    );

    entries.push({
      version,
      title,
      date,
      userSummary: (userBlock?.[1] ?? "").trim(),
      technicalDetails: (techBlock?.[1] ?? "").trim(),
    });
  }

  return entries;
}

/**
 * Render a tiny subset of markdown to JSX-safe HTML:
 *   - `inline code` → <code>
 *   - **bold** → <strong>
 *   - `- bullet` lines collapse into a single <ul>
 *   - blank lines split paragraphs
 *
 * We do not need a full markdown parser; CHANGELOG.md uses only these.
 */
export function renderMarkdownBlock(md: string): string {
  if (!md) return "";

  const lines = md.split("\n");
  const out: string[] = [];
  let inList = false;

  const inline = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  let paragraph: string[] = [];
  const flushParagraph = () => {
    if (paragraph.length) {
      out.push(`<p>${inline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (line.startsWith("- ")) {
      flushParagraph();
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline(line.slice(2))}</li>`);
    } else if (line.trim() === "") {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      flushParagraph();
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      paragraph.push(line.trim());
    }
  }

  if (inList) out.push("</ul>");
  flushParagraph();

  return out.join("\n");
}
