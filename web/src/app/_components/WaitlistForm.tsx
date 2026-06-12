"use client";

import { useState } from "react";

type Status = "idle" | "sending" | "ok" | "error";

export function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status === "sending") return;

    setStatus("sending");
    setMessage("");

    try {
      const res = await fetch("/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (res.ok) {
        setStatus("ok");
        setMessage("You're on the list. We'll email when the installer ships.");
        setEmail("");
      } else {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        if (body.error === "invalid_email") {
          setStatus("error");
          setMessage("That email doesn't look right.");
        } else {
          setStatus("error");
          setMessage("Something went wrong. Try again in a minute?");
        }
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Try again in a minute?");
    }
  }

  return (
    <div>
      <form className="waitlist-form" onSubmit={onSubmit}>
        <input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={status === "sending"}
          aria-label="Email address"
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={status === "sending"}
        >
          {status === "sending" ? "Adding…" : "Notify me"}
        </button>
      </form>
      {message && (
        <p
          className={`waitlist-status ${status === "ok" ? "ok" : status === "error" ? "err" : ""}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
