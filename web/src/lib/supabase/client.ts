"use client";

import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * Minimal Supabase browser client.
 *
 * Daisy is a local-first Mac app — the website does not need user accounts,
 * cookies, or SSR auth. The only cloud touchpoint is the waitlist form, which
 * fires-and-forgets an INSERT into `public.daisy_waitlist`.
 *
 * Anon role has INSERT privilege via RLS policy (no SELECT) so emails cannot
 * be enumerated from the client.
 */
export function createClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    },
  );
}

export type AppSupabaseClient = ReturnType<typeof createClient>;
