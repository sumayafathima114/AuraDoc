"use client";

import { FormEvent, useState } from "react";
import { useEffect } from "react";
import { createClient } from "@/lib/supabase/browser";
import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

type LegalSource = { id: string; case_id: string; case_title: string; title: string; source_type: string; authority: string; act_or_regulation: string | null; section: string | null; version_label: string | null; effective_date: string | null; official_source_url: string; verification_status: string; verified_at: string | null };
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function LegalIntelligenceClient() {
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [sources, setSources] = useState<LegalSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => { const controller = new AbortController(); let disposed = false; let timedOut = false; let timeout = 0; void (async () => {
    try {
      const { data: { session } } = await createClient().auth.getSession();
      if (disposed) return;
      if (!session) { location.assign("/signin"); return; }
      timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 15_000);
      const response = await fetch(`${api}/api/v1/legal-sources`, { headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error("Your case-linked legal-source records could not be loaded.");
      const records = await response.json();
      if (!disposed) { setSources(records); setError(""); }
    } catch (e) {
      if (disposed) return;
      setError(timedOut ? "Loading legal-source records timed out. Check FastAPI and retry." : e instanceof TypeError ? "FastAPI is unavailable. Start the backend and retry." : e instanceof Error ? e.message : "Legal sources could not be loaded.");
    } finally {
      window.clearTimeout(timeout);
      if (!disposed) setLoading(false);
    }
  })(); return () => { disposed = true; window.clearTimeout(timeout); controller.abort(); }; }, [retry]);
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = query.trim();
    if (!q) { setError("Enter a search term to open an official source portal."); return; }
    setError("");
    window.open(`https://www.indiacode.nic.in/handle/123456789/1362/simple-search?query=${encodeURIComponent(q)}&rpp=10&sort_by=score`, "_blank", "noopener,noreferrer");
  }
  return <WorkspaceShell active="/legal-intelligence"><div className="ad-page-heading"><div><p className="ad-eyebrow">OFFICIAL SOURCE ACCESS</p><h1>Legal Intelligence</h1><p className="ad-lead">Search authoritative Indian legal portals. AuraDoc does not treat model output as law.</p></div></div>
    <section className="ad-legal-intro"><span className="ad-source-seal">IN</span><div><p className="ad-eyebrow">SOURCE POLICY</p><h2>Primary sources first. Human verification always.</h2><p>Search the official India Code portal for legislation, or the Supreme Court of India portal for judgments and orders. These links open the external official sites; AuraDoc has not imported, independently verified, or checked the current applicability of the results.</p></div></section>
    <div className="ad-legal-grid"><section className="ad-panel"><p className="ad-eyebrow">LEGISLATION · GOVERNMENT OF INDIA</p><h2>India Code</h2><p className="ad-body-copy">Search legislation using a keyword. Confirm the Act, section, amendment history, effective date, and status on the official source.</p><form className="ad-search-form" onSubmit={search}><label htmlFor="legal-query">Keyword or phrase</label><div><input id="legal-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Enter a search term" maxLength={160}/><button className="ad-primary-button" type="submit">Search India Code ↗</button></div></form>{error && <p className="ad-error" role="alert">{error}</p>}<a className="ad-official-link" href="https://www.indiacode.nic.in/" target="_blank" rel="noreferrer">Open India Code home ↗</a><p className="ad-source-meta">Official portal · Government of India · External search, not an AuraDoc-verified result</p></section>
    <section className="ad-panel"><p className="ad-eyebrow">COURT MATERIAL</p><h2>Supreme Court of India</h2><p className="ad-body-copy">Use the Court’s official search portal for judgments and orders. The portal may require CAPTCHA and additional search steps.</p><a className="ad-primary-button ad-button-inline" href="https://scr.sci.gov.in/scrsearch/" target="_blank" rel="noreferrer">Open official judgment search ↗</a><a className="ad-official-link" href="https://www.sci.gov.in/" target="_blank" rel="noreferrer">Supreme Court of India home ↗</a><p className="ad-source-meta">Official court portal · Verify case metadata and the judgment text at source</p></section></div>
    <section className="ad-panel ad-source-library"><div className="ad-panel-heading"><div><p className="ad-eyebrow">CASE-LINKED RECORDS</p><h2>Legal source evidence</h2></div></div>{error && <p className="ad-error" role="alert">{error} <button className="ad-retry-button" onClick={() => { setLoading(true); setRetry((value) => value + 1); }}>Retry</button></p>}{loading ? <p className="ad-muted">Loading your case-linked source records…</p> : sources.length ? <div className="ad-source-record-list">{sources.map((source) => <article key={source.id}><div><span className={`ad-source-status ${source.verification_status.toLowerCase()}`}>{source.verification_status === "VERIFIED_OFFICIAL" ? "SOURCE VERIFIED · HUMAN ATTESTED" : source.verification_status.replaceAll("_", " ")}</span><h3>{source.title}</h3><p>{[source.authority, source.act_or_regulation, source.section && `Section ${source.section}`, source.version_label, source.effective_date && `Effective ${source.effective_date}`].filter(Boolean).join(" · ")}</p><small>Case: {source.case_title}</small></div><div className="ad-source-actions"><a href={source.official_source_url} target="_blank" rel="noreferrer">Inspect official URL ↗</a><a href={`/cases/${source.case_id}`}>Open case record →</a></div></article>)}</div> : <p className="ad-empty-text">No case-linked legal-source records exist yet. Add source text from an official portal in a case workspace; every new record starts pending human verification.</p>}</section>
    <section className="ad-verification-note"><h2>Verification state</h2><p>Portal search results are external references. A case source is marked <strong>VERIFIED OFFICIAL</strong> only after an authorized reviewer attests that they checked its official URL, source text and version. AuraDoc does not independently authenticate portal content or determine current applicability.</p><p className="ad-human-note">Legal interpretation and final decisions require human review. AuraDoc does not establish liability, guilt, truthfulness, or admissibility.</p></section>
  </WorkspaceShell>;
}
