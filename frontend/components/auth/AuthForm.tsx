"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { createClient } from "@/lib/supabase/browser";

type Mode = "signin" | "signup" | "reset" | "complete";

export function AuthForm({ mode }: { mode: Mode }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); setError("");
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    try {
      const supabase = createClient();
      if (mode === "signup") {
        const { error: authError } = await supabase.auth.signUp({ email, password, options: { emailRedirectTo: `${location.origin}/auth/callback?next=%2Fdashboard` } });
        if (authError) throw authError;
        setMessage("If registration is enabled, check your email to confirm your account.");
      } else if (mode === "signin") {
        const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
        if (authError) throw authError;
        const next = new URLSearchParams(location.search).get("next");
        let destination = "/dashboard";
        const hasControlCharacter = next ? Array.from(next).some((character) => character.charCodeAt(0) < 32) : false;
        if (next?.startsWith("/") && !next.startsWith("//") && !next.includes("\\") && !hasControlCharacter) {
          try {
            const parsed = new URL(next, location.origin);
            if (parsed.origin === location.origin) destination = `${parsed.pathname}${parsed.search}${parsed.hash}`;
          } catch {
            // Keep the safe dashboard default for malformed redirect values.
          }
        }
        location.assign(destination);
      } else if (mode === "reset") {
        const { error: authError } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/auth/callback?next=%2Freset-password` });
        if (authError) throw authError;
        setMessage("If an account matches that address, a password reset link will arrive shortly.");
      } else {
        const { error: authError } = await supabase.auth.updateUser({ password });
        if (authError) throw authError;
        setMessage("Password updated. You can now sign in with your new password.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The request could not be completed.");
    } finally { setBusy(false); }
  }
  const title = mode === "signin" ? "Welcome back" : mode === "signup" ? "Request access" : mode === "reset" ? "Reset your password" : "Choose a new password";
  return <main className="auth-shell"><section className="auth-card"><Link href="/" className="wordmark"><span className="mark">A</span>AuraDoc</Link><p className="eyebrow">PRIVATE FORENSIC WORKBENCH</p><h1>{title}</h1><p className="auth-intro">Secure access. Confidential by design. Your evidence remains under human review.</p><form onSubmit={submit} className="auth-form">{mode !== "complete" && <label>Email address<input name="email" type="email" autoComplete="email" required /></label>}{mode !== "reset" && <label>{mode === "signin" ? "Password" : "New password"}<input name="password" type="password" minLength={8} autoComplete={mode === "signin" ? "current-password" : "new-password"} required /></label>}{error && <p role="alert" className="form-error">{error}</p>}{message && <p role="status" className="form-message">{message}</p>}<button className="auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "signin" ? "Sign in" : mode === "signup" ? "Create account" : mode === "reset" ? "Send reset link" : "Update password"}</button></form><nav className="auth-links">{mode !== "signin" && <Link href="/signin">Back to sign in</Link>}{mode === "signin" && <><Link href="/forgot-password">Forgot password?</Link><span>New to AuraDoc? <Link href="/signup">Request access</Link></span></>}</nav><p className="legal-note">AuraDoc supports evidence review. It does not make legal determinations.</p></section></main>;
}
