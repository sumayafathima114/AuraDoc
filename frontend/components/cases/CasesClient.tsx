"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/browser";
import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

type CaseRecord = { id: string; case_number: string; title: string; description: string; status: string; created_at: string };
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function responseError(response: Response, fallback: string): Promise<Error> {
  if (response.status === 401) {
    location.assign("/signin");
    return new Error("Your session expired. Sign in again.");
  }
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
      return new Error(body.detail);
    }
  } catch {
    // Keep a safe user-facing fallback for empty or non-JSON gateway errors.
  }
  if (response.status === 403) return new Error("You are not authorized to access these cases.");
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return new Error("AuraDoc could not reach its case database. Confirm FastAPI is running and Supabase is configured.");
  }
  return new Error(fallback);
}

export function CasesClient() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseRecord[]>([]); const [title, setTitle] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  async function load() {
    const controller = new AbortController(); let timedOut = false;
    const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 15_000);
    setLoading(true); setError("");
    try {
      const supabase = createClient(); const { data: { session } } = await supabase.auth.getSession();
      if (!session) { location.assign("/signin"); return; }
      const response = await fetch(`${api}/api/v1/cases`, { headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store", signal: controller.signal });
      if (!response.ok) throw await responseError(response, "Cases could not be loaded.");
      setCases(await response.json());
    } catch (caught) {
      setError(timedOut ? "Loading cases timed out. Check FastAPI and Supabase, then retry." : caught instanceof TypeError ? "FastAPI is unavailable. Start the backend and try again." : caught instanceof Error ? caught.message : "Cases could not be loaded.");
    } finally { window.clearTimeout(timeout); setLoading(false); }
  }
  useEffect(() => { void load(); }, [retry]);
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(""); try {
    const supabase = createClient(); const { data: { session } } = await supabase.auth.getSession();
    if (!session) throw new Error("Your session expired. Sign in again.");
    const response = await fetch(`${api}/api/v1/cases`, { method: "POST", headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" }, body: JSON.stringify({ title, description: "" }) });
    if (!response.ok) throw await responseError(response, "The case could not be created.");
    const created = await response.json() as CaseRecord; setTitle(""); router.push(`/cases/${created.id}`);
  } catch (e) { setError(e instanceof Error ? e.message : "The case could not be created."); } finally { setBusy(false); } }
  return <WorkspaceShell active="/cases"><div className="app-shell"><header className="app-top"><Link href="/dashboard">Dashboard</Link><span>CASE REGISTER</span></header><section className="app-content"><p className="eyebrow">INVESTIGATION WORKSPACE</p><h1>Your cases</h1><p className="app-lead">Evidence and review records are isolated by case membership.</p><form onSubmit={create} className="create-case"><label htmlFor="case-title">Open a new investigation</label><div><input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} placeholder="Case title"/><button disabled={busy || loading}>{busy ? "Creating…" : "Create case"}</button></div></form>{error && <p role="alert" className="form-error">{error} <button className="ad-retry-button" onClick={() => setRetry((value) => value + 1)}>Retry</button></p>}<div className="case-list" aria-live="polite">{loading && <p className="empty-state">Loading your cases…</p>}{!loading && cases.map((item) => <Link key={item.id} href={`/cases/${item.id}`} className="case-tile"><span className="case-id">{item.case_number} · {item.status}</span><strong>{item.title}</strong><small>Created {new Date(item.created_at).toLocaleDateString()}</small><span className="case-open">Open case →</span></Link>)}{!loading && !cases.length && !error && <p className="empty-state">No cases yet. Create an investigation to begin.</p>}</div></section></div></WorkspaceShell>;
}
