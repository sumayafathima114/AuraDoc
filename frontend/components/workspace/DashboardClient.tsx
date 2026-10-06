"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/browser";
import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

type DashboardData = {
  profile: { display_name: string; email: string | null };
  stats: { active_cases: number; awaiting_review: number; possible_discrepancies: number; insufficient_evidence: number; human_verified: number; evidence_items: number; pending_actions: number; legal_intelligence_items: number; recommendations: number };
  cases: { id: string; case_number: string; title: string; status: string; updated_at: string; evidence_count: number; finding_count: number; document_status: string; audio_status: string; finding_status: string; review_status: string }[];
  findings: { id: string; case_id: string; case_title: string; relation_type: string; status: string; summary: string }[];
  activity: { id: string; case_id: string; case_title: string; action: string; entity_type: string; created_at: string }[];
};
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const statLabels = [["active_cases", "Active cases"], ["awaiting_review", "Pending reviews"], ["possible_discrepancies", "Possible discrepancies"], ["insufficient_evidence", "Insufficient evidence"], ["legal_intelligence_items", "Legal analyses"], ["recommendations", "Open recommendations"], ["human_verified", "Human verified"], ["evidence_items", "Source files"]] as const;

export function DashboardClient() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 15_000);
    void (async () => {
      setLoading(true);
      setError("");
      try {
        const { data: { session } } = await createClient().auth.getSession();
        if (!session) { location.assign("/signin"); return; }
        const response = await fetch(`${api}/api/v1/dashboard`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.status === 401) { location.assign("/signin"); return; }
        if (!response.ok) throw new Error("Dashboard data could not be loaded. Check the FastAPI service and try again.");
        setData(await response.json());
      } catch (e) {
        if (controller.signal.aborted && !timedOut) return;
        setError(timedOut
          ? "Dashboard data took too long to load. Check FastAPI and Supabase, then retry."
          : e instanceof TypeError
            ? "FastAPI is unavailable. Start the backend and retry."
            : e instanceof Error ? e.message : "Dashboard data could not be loaded.");
      } finally {
        window.clearTimeout(timeout);
        if (!controller.signal.aborted || timedOut) setLoading(false);
      }
    })();
    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [retry]);
  const name = data?.profile.display_name.trim();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  return <WorkspaceShell active="/dashboard"><div className="ad-page-heading"><div><p className="ad-eyebrow">INVESTIGATION OVERVIEW</p><h1>{name ? `${greeting}, ${name}` : "Your investigation workspace"}</h1><p className="ad-lead">Your forensic and legal evidence workspace.</p></div><Link className="ad-primary-button" href="/cases">Open case workspace <span aria-hidden>→</span></Link></div>
    {error && <div className="ad-error" role="alert"><span>{error}</span> <button className="ad-retry-button" onClick={() => setRetry((attempt) => attempt + 1)}>Retry</button></div>}
    <section className="ad-stat-grid" aria-label="Case statistics">{statLabels.map(([key, label]) => <article className="ad-stat-card" key={key}><span>{label}</span><strong>{loading ? "—" : data?.stats[key]}</strong><small>{loading ? "Loading account data" : "From the latest 100 accessible records"}</small></article>)}</section>
    <div className="ad-dashboard-grid"><section className="ad-panel ad-recent-cases"><div className="ad-panel-heading"><div><p className="ad-eyebrow">CASE REGISTER</p><h2>Recent cases</h2></div><Link href="/cases">All cases →</Link></div>
      {loading ? <p className="ad-muted">Loading cases…</p> : data?.cases.length ? <div className="ad-table-wrap"><table className="ad-table"><thead><tr><th>Case ID</th><th>Case name</th><th>Status</th><th>Document</th><th>Audio</th><th>Finding</th><th>Review</th><th>Updated</th></tr></thead><tbody>{data.cases.map((item) => <tr key={item.id}><td>{item.case_number}</td><td><Link href={`/cases/${item.id}`}>{item.title}</Link></td><td><span className="ad-status">{item.status.replaceAll("_", " ")}</span></td><td>{item.document_status.replaceAll("_", " ")}</td><td>{item.audio_status.replaceAll("_", " ")}</td><td>{item.finding_status.replaceAll("_", " ")}</td><td>{item.review_status.replaceAll("_", " ")}</td><td>{new Date(item.updated_at).toLocaleDateString()}</td></tr>)}</tbody></table><small className="ad-muted">Records are summarized from the latest 100 accessible records by type.</small></div> : <div className="ad-empty"><p>No investigations yet.</p><Link href="/cases">Create your first case →</Link></div>}</section>
      <section className="ad-panel"><div className="ad-panel-heading"><div><p className="ad-eyebrow">HUMAN REVIEW</p><h2>Recent findings</h2></div><Link href="/cases">View cases →</Link></div>
      {loading ? <p className="ad-muted">Loading findings…</p> : data?.findings.length ? <ul className="ad-list">{data.findings.slice(0, 6).map((finding) => <li key={finding.id}><span className="ad-finding-mark">◇</span><div><strong>{finding.relation_type.replaceAll("_", " ")}</strong><p>{finding.summary}</p><small>{finding.case_title} · {finding.status.replaceAll("_", " ")}</small></div></li>)}</ul> : <p className="ad-empty-text">No findings have been recorded for your cases.</p>}</section>
      <section className="ad-panel"><div className="ad-panel-heading"><div><p className="ad-eyebrow">AUDIT TRAIL</p><h2>Recent activity</h2></div></div>
      {loading ? <p className="ad-muted">Loading activity…</p> : data?.activity.length ? <ul className="ad-activity">{data.activity.map((item) => <li key={item.id}><time>{new Date(item.created_at).toLocaleString()}</time><strong>{item.action.replaceAll("_", " ")}</strong><span>{item.case_title}</span></li>)}</ul> : <p className="ad-empty-text">Audit activity will appear as work is recorded.</p>}</section>
      <section className="ad-panel ad-quick-panel"><p className="ad-eyebrow">QUICK ACCESS</p><h2>Continue your work</h2><div className="ad-quick-links"><Link href="/cases">Cases <span>→</span></Link><Link href="/legal-intelligence">Official legal sources <span>→</span></Link><Link href="/profile">Your profile <span>→</span></Link></div><p className="ad-disclaimer">AuraDoc organizes evidence and supports research. Human reviewers remain responsible for legal and investigative decisions.</p></section>
    </div>
  </WorkspaceShell>;
}
