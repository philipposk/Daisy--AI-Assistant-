import { WaitlistForm } from "./_components/WaitlistForm";

const FEATURES = [
  {
    icon: "🎙️",
    title: "Wake & talk",
    body: 'Say "Daisy" — she listens, replies out loud, and shuts up the moment you say "stop".',
  },
  {
    icon: "📅",
    title: "Calendar & Mail",
    body: "Books events, drafts emails through Mail.app, reads your inbox — all by voice.",
  },
  {
    icon: "📝",
    title: "Notes & reminders",
    body: '"Make a note about the Q3 launch." "Remind me in 2 hours to drink water." Done.',
  },
  {
    icon: "🧠",
    title: "Remembers you",
    body: "Tell her once you prefer Python or your dog is Rex. She still knows next week.",
  },
  {
    icon: "↩️",
    title: "Undo",
    body: 'Say "undo that" — last note, task, reminder, or memory is reversed.',
  },
  {
    icon: "🔌",
    title: "MCP-powered",
    body: "Both an MCP server and client — drives desktop automation and computer-use tools.",
  },
];

const FAQ = [
  {
    q: "Is Daisy Mac only?",
    a: "Yes. She talks to Calendar, Mail, and Reminders through AppleScript, and stores API keys in the macOS Keychain. Linux/Windows ports aren't planned.",
  },
  {
    q: "How much does Daisy cost?",
    a: "Daisy herself is free and open source (MIT). You pay your AI provider directly — or run Ollama locally and pay $0 total.",
  },
  {
    q: "Which AI providers are supported?",
    a: "OpenAI, Anthropic, Groq, or local Ollama. You configure a fallback chain so she keeps working if one provider rate-limits you.",
  },
  {
    q: "What permissions does she need?",
    a: "Microphone (to hear you), Accessibility (to control apps), Calendar / Mail / Reminders (to read and write them), and optionally Screen Recording for screenshot features. macOS prompts you for each one.",
  },
  {
    q: "Is she always listening?",
    a: 'Only for her wake word ("Daisy"). Once she\'s replying, you can interrupt at any time by saying "stop". No audio is sent anywhere until you trigger a turn.',
  },
  {
    q: "Can she start automatically when I log in?",
    a: "Yes — new in v1.5. Run `python3 tools/launchd_setup.py install` and she'll run quietly in the background, restarting herself if she crashes.",
  },
];

export default function Home() {
  return (
    <div style={{ maxWidth: "56rem", margin: "0 auto", padding: "3rem 1.5rem 6rem" }}>
      {/* ────────────── 1. HERO ────────────── */}
      <section>
        <p className="section-kicker">Mac voice assistant</p>
        <h1
          style={{
            fontSize: "clamp(2rem, 5vw, 3.5rem)",
            fontWeight: 800,
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            marginBottom: "1.25rem",
          }}
        >
          A polite voice assistant
          <br />
          that lives on your Mac.
        </h1>
        <p style={{ color: "var(--accent)", fontWeight: 600, fontSize: "1.15rem", marginBottom: "1rem" }}>
          Gets things done without nagging.
        </p>
        <p
          style={{
            color: "var(--fg-muted)",
            fontSize: "1.1rem",
            lineHeight: 1.6,
            maxWidth: "36rem",
            marginBottom: "2rem",
          }}
        >
          Daisy runs quietly in the background on macOS. Say the word, and she takes
          notes, sets reminders, reads your calendar, drafts emails, and remembers what
          matters — then gets out of the way.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
          <a href="#install" className="btn btn-primary">
            Download for macOS →
          </a>
          <a
            href="https://github.com/philipposk/Daisy--AI-Assistant-"
            className="btn btn-ghost"
            target="_blank"
            rel="noopener noreferrer"
          >
            View on GitHub
          </a>
        </div>
        <p style={{ color: "var(--fg-muted)", fontSize: "0.8rem" }}>
          macOS · Open source · MIT · v1.5 stable
        </p>

        {/* Demo video */}
        <div className="hero-media" style={{ border: "none", overflow: "hidden", padding: 0 }}>
          <video
            src="/daisy-demo.mp4"
            controls
            autoPlay
            muted
            loop
            playsInline
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        </div>
      </section>

      {/* ────────────── 2. FEATURES ────────────── */}
      <section className="section" id="features">
        <p className="section-kicker">What she does</p>
        <h2 className="section-title">Six things she's good at.</h2>
        <p className="section-lede">
          Daisy isn't a chatbot in a window. She lives in your menu bar, listens for her
          name, and uses the apps you already have.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1rem",
          }}
        >
          {FEATURES.map((f) => (
            <div key={f.title} className="glass" style={{ padding: "1.5rem" }}>
              <div style={{ fontSize: "1.75rem", marginBottom: "0.75rem" }}>{f.icon}</div>
              <h3 style={{ fontWeight: 700, marginBottom: "0.5rem" }}>{f.title}</h3>
              <p style={{ color: "var(--fg-muted)", fontSize: "0.9rem", lineHeight: 1.5 }}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ────────────── 3. INSTALL ────────────── */}
      <section className="section" id="install">
        <p className="section-kicker">Install</p>
        <h2 className="section-title">Two ways to get her.</h2>
        <p className="section-lede">
          v1.5 is the current stable release. Source install works today; a signed{" "}
          <code>.dmg</code> installer is on the way.
        </p>

        <div className="install-grid">
          {/* Source install */}
          <div className="glass" style={{ padding: "1.5rem" }}>
            <span className="install-tag">Available now</span>
            <h3 style={{ fontWeight: 700, marginBottom: "0.5rem" }}>From GitHub</h3>
            <p style={{ color: "var(--fg-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
              Clone the repo, run the setup script, open the local web UI.
            </p>
            <pre className="code-block">
              <code>{`git clone https://github.com/philipposk/Daisy--AI-Assistant-
cd "Daisy -AI Assistant- 1.5"
./setup.sh
python3 daisy_app.py --port 5188
open http://localhost:5188/`}</code>
            </pre>
            <p style={{ color: "var(--fg-muted)", fontSize: "0.85rem", marginTop: "0.85rem" }}>
              You&apos;ll also need an API key (OpenAI, Anthropic, Groq, or local Ollama).
              Stored in the macOS Keychain — never on disk in plain text.
            </p>
          </div>

          {/* .dmg installer (coming soon) */}
          <div className="glass" style={{ padding: "1.5rem" }}>
            <span className="install-tag muted">Coming soon</span>
            <h3 style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
              Signed <code>.dmg</code>
            </h3>
            <p style={{ color: "var(--fg-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
              Double-click to install. No Python, no terminal. Notarized for Gatekeeper.
            </p>
            <a href="#waitlist" className="btn btn-ghost" style={{ fontSize: "0.85rem" }}>
              Get notified →
            </a>
          </div>
        </div>
      </section>

      {/* ────────────── 4. PRIVACY ────────────── */}
      <section className="section" id="privacy">
        <p className="section-kicker">Privacy & trust</p>
        <h2 className="section-title">Local-first by design.</h2>
        <p className="section-lede">
          Daisy is your assistant, not someone else&apos;s product. Here&apos;s what that
          means in practice.
        </p>
        <ul
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1rem",
            listStyle: "none",
            padding: 0,
          }}
        >
          {[
            {
              t: "Keys in the Keychain",
              d: "API keys live in the macOS Keychain — the same secure store your Mac uses for Wi-Fi passwords. Never written to disk or committed to git.",
            },
            {
              t: "No telemetry",
              d: "No analytics, no crash reporting, no usage pings. Daisy never phones home.",
            },
            {
              t: "No account needed",
              d: "No login, no sign-up, no cloud. You don't have an account because there isn't one to have.",
            },
            {
              t: "Your data stays local",
              d: "Notes, reminders, memory, audit log — all stored on your Mac. The only outbound calls are to the AI provider you choose.",
            },
            {
              t: "Audit log + undo",
              d: 'Every action she takes is logged. Say "undo that" and she reverses the last note, task, reminder, or memory.',
            },
            {
              t: "MIT licensed",
              d: "Source on GitHub. Read it, fork it, run it forever — no vendor lock-in.",
            },
          ].map((p) => (
            <li key={p.t} className="glass" style={{ padding: "1.25rem" }}>
              <h3 style={{ fontWeight: 700, marginBottom: "0.4rem", fontSize: "1rem" }}>{p.t}</h3>
              <p style={{ color: "var(--fg-muted)", fontSize: "0.88rem", lineHeight: 1.55 }}>{p.d}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ────────────── 5. FAQ ────────────── */}
      <section className="section" id="faq">
        <p className="section-kicker">FAQ</p>
        <h2 className="section-title">Questions people ask.</h2>
        <div style={{ marginTop: "1.5rem" }}>
          {FAQ.map((item) => (
            <details className="faq" key={item.q}>
              <summary>{item.q}</summary>
              <div>{item.a}</div>
            </details>
          ))}
        </div>
      </section>

      {/* ────────────── 6. WAITLIST ────────────── */}
      <section className="section" id="waitlist">
        <p className="section-kicker">Waitlist</p>
        <h2 className="section-title">Get the installer when it&apos;s ready.</h2>
        <p className="section-lede">
          One email when the signed <code>.dmg</code> ships. No newsletter, no marketing,
          no sharing. Unsubscribe in one click whenever you want.
        </p>
        <WaitlistForm />
      </section>
    </div>
  );
}
