import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Daisy — Your polite Mac voice assistant",
  description:
    "A polite AI voice assistant that lives on your Mac and gets things done without nagging. Open source, MIT, v1.6 stable.",
  applicationName: "Daisy",
};

export const viewport: Viewport = { themeColor: "#07070a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <nav
          style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
          className="px-6 py-4 flex items-center justify-between"
        >
          <Link
            href="/"
            style={{
              color: "var(--accent)",
              fontWeight: 700,
              fontSize: "1.1rem",
              textDecoration: "none",
            }}
          >
            Daisy
          </Link>
          <div style={{ display: "flex", alignItems: "center" }}>
            <Link href="/changelog" className="nav-link">
              Changelog
            </Link>
            <a
              href="https://github.com/philipposk/Daisy--AI-Assistant-"
              className="nav-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
            <a href="https://6x7.gr" className="nav-link">
              by 6x7.gr
            </a>
          </div>
        </nav>
        <main className="flex-1">{children}</main>
        <footer
          style={{
            borderTop: "1px solid rgba(255,255,255,0.06)",
            color: "var(--fg-muted)",
            fontSize: "0.75rem",
            textAlign: "center",
            padding: "1.5rem",
          }}
        >
          Daisy · v1.6 stable ·{" "}
          <Link href="/changelog" style={{ color: "var(--accent)" }}>
            changelog
          </Link>{" "}
          · part of{" "}
          <a href="https://6x7.gr" style={{ color: "var(--accent)" }}>
            6x7.gr
          </a>
        </footer>
      </body>
    </html>
  );
}
