import { NextResponse } from "next/server";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * POST /waitlist  { email: string }
 *
 * Inserts into `public.daisy_waitlist`. RLS allows anon INSERT only, so the
 * publishable key is safe to use server-side too. Duplicate emails are
 * silently treated as success (the user already signed up).
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const email = (body as { email?: unknown })?.email;
  if (typeof email !== "string" || !isValidEmail(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    return NextResponse.json({ error: "server_misconfigured" }, { status: 500 });
  }

  const supabase = createSupabaseClient(url, anonKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
    },
  });

  const { error } = await supabase
    .from("daisy_waitlist")
    .insert({ email: email.trim().toLowerCase() });

  // 23505 = unique_violation — already on the list, treat as success.
  if (error && error.code !== "23505") {
    return NextResponse.json({ error: "insert_failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}

function isValidEmail(email: string): boolean {
  // Pragmatic check — full RFC 5322 is overkill for a marketing waitlist.
  // Trim, require exactly one @, non-empty local part, dotted domain.
  const trimmed = email.trim();
  if (trimmed.length > 254) return false;
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(trimmed);
}
