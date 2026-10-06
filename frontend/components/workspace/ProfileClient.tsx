"use client";

import { FormEvent, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/browser";
import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export function ProfileClient() {
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const [message, setMessage] = useState("");
  useEffect(() => { void (async () => {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) { location.assign("/signin"); return; }
    try { const response = await fetch(`${api}/api/v1/profile`, { headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store" });
      if (!response.ok) throw new Error("Profile could not be loaded.");
      const profile = await response.json(); setName(profile.display_name); setEmail(profile.email ?? "");
    } catch (e) { setError(e instanceof Error ? e.message : "Profile could not be loaded."); }
    finally { setLoading(false); }
  })(); }, []);
  async function save(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const { data: { session } } = await createClient().auth.getSession(); if (!session) throw new Error("Your session expired. Sign in again.");
      const response = await fetch(`${api}/api/v1/profile`, { method: "PATCH", headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" }, body: JSON.stringify({ display_name: name }) });
      if (!response.ok) throw new Error("Profile could not be updated."); const updated = await response.json(); setName(updated.display_name); setMessage("Display name saved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Profile could not be updated."); } finally { setBusy(false); }
  }
  return <WorkspaceShell active="/profile"><div className="ad-page-heading"><div><p className="ad-eyebrow">ACCOUNT</p><h1>Your profile</h1><p className="ad-lead">Manage the small amount of profile information used in AuraDoc.</p></div></div>
    {error && <p className="ad-error" role="alert">{error}</p>}
    <section className="ad-panel ad-profile-panel"><div className="ad-profile-monogram" aria-hidden>{name.trim() ? name.trim().charAt(0).toUpperCase() : "A"}</div><div><p className="ad-eyebrow">AUTHENTICATED ACCOUNT</p><h2>{name.trim() || "Display name not provided"}</h2><p className="ad-profile-email">{email}</p></div></section>
    <form className="ad-panel ad-profile-form" onSubmit={save}><h2>Professional display</h2><p className="ad-body-copy">Only your display name is stored in the current AuraDoc profile schema. No role, qualification, organization, photo, or jurisdiction is assumed.</p><label htmlFor="display-name">Display name</label><input id="display-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={120} disabled={loading}/>{error && <p className="ad-error" role="alert">{error}</p>}{message && <p className="ad-success" role="status">{message}</p>}<button className="ad-primary-button" disabled={loading || busy}>{busy ? "Saving…" : "Save display name"}</button></form>
  </WorkspaceShell>;
}
