import Link from "next/link";
import type { Metadata } from "next";
import { readChangelog, renderMarkdownBlock } from "@/lib/changelog";

export const metadata: Metadata = {
  title: "Changelog — Daisy",
  description: "Every release of Daisy from 0.5 to 1.5 stable.",
};

export default async function ChangelogPage() {
  const entries = await readChangelog();
  const current = entries[0]?.version;

  return (
    <div style={{ maxWidth: "56rem", margin: "0 auto", padding: "3rem 1.5rem 6rem" }}>
      <div style={{ marginBottom: "3rem" }}>
        <Link
          href="/"
          style={{ color: "var(--fg-muted)", fontSize: "0.85rem", textDecoration: "none" }}
        >
          ← Back to Daisy
        </Link>
        <h1
          style={{
            fontSize: "clamp(2rem, 4vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.02em",
            marginTop: "1rem",
            marginBottom: "0.75rem",
          }}
        >
          Changelog
        </h1>
        <p style={{ color: "var(--fg-muted)", fontSize: "1.05rem", lineHeight: 1.6 }}>
          Every release from the first proof-of-concept (0.5) to today&apos;s stable (
          {current ?? "1.5"}). Each entry tells you what changed in plain English first,
          then the technical detail.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {entries.map((e, i) => {
          const isCurrent = i === 0;
          return (
            <article
              key={e.version}
              className="glass"
              style={{
                padding: "1.75rem",
                borderColor: isCurrent ? "var(--accent)" : undefined,
                borderWidth: isCurrent ? "1px" : undefined,
              }}
            >
              <header
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "baseline",
                  gap: "0.75rem",
                  marginBottom: "1rem",
                }}
              >
                <h2
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    letterSpacing: "-0.01em",
                  }}
                >
                  {e.version}
                </h2>
                {e.title && (
                  <span style={{ color: "var(--fg)", fontWeight: 600 }}>{e.title}</span>
                )}
                {isCurrent && (
                  <span
                    style={{
                      background: "var(--accent)",
                      color: "#000",
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "0.15rem 0.55rem",
                      borderRadius: "9999px",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                    }}
                  >
                    Current stable
                  </span>
                )}
                {e.date && (
                  <span style={{ color: "var(--fg-muted)", fontSize: "0.85rem", marginLeft: "auto" }}>
                    {e.date}
                  </span>
                )}
              </header>

              {e.userSummary && (
                <div
                  className="changelog-prose"
                  dangerouslySetInnerHTML={{ __html: renderMarkdownBlock(e.userSummary) }}
                />
              )}

              {e.technicalDetails && (
                <details style={{ marginTop: "1rem" }}>
                  <summary
                    style={{
                      cursor: "pointer",
                      color: "var(--fg-muted)",
                      fontSize: "0.85rem",
                      fontWeight: 600,
                    }}
                  >
                    Technical details
                  </summary>
                  <div
                    className="changelog-prose"
                    style={{ marginTop: "0.75rem", color: "var(--fg-muted)", fontSize: "0.9rem" }}
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdownBlock(e.technicalDetails),
                    }}
                  />
                </details>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
