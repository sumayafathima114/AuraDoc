"use client";

import { FormEvent, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/browser";

export type Source = { id: string; title: string; source_type: string; jurisdiction: string; authority: string; act_or_regulation: string | null; section: string | null; subsection: string | null; publication_date: string | null; effective_date: string | null; version_label: string | null; official_source_url: string; verification_status: string; source_text: string; source_sha256: string; verified_at: string | null; verification_notes: string | null };
export type Finding = { id: string; analysis_mode?: string; relation_type: string; summary: string; explanation: string; uncertainties: string[]; status: string; provider: string; model_name: string };
type Relevance = { legal_source_id: string; why_may_matter: string; evidence_connection: string; limitations: string };
export type LegalAnalysis = { id: string; finding_id: string; status: string; legal_relevance: Relevance[]; missing_evidence: string[]; provider: string | null; model_name: string | null; created_at: string; requires_human_review: boolean };
export type Recommendation = { id: string; finding_id: string; action: string; reason: string; evidence_basis: string; priority: string; status: string; legal_source_id: string | null };
export type ReviewAction = { id: string; finding_id: string; decision: string; comment: string | null; reviewer_notes: string | null; previous_status: string | null; new_status: string | null; reviewed_at: string };
export type HumanConclusion = { id: string; case_id: string; finding_id: string; reviewer_user_id: string; lawyer_recommendation: string; human_conclusion: string; limitations: string; finding_snapshot: Record<string, unknown>; evidence_snapshot: unknown[]; verified_sources_snapshot: unknown[]; recommendations_snapshot: unknown[]; created_at: string };
type Props = { caseId: string; findings: Finding[]; sources: Source[]; analyses: LegalAnalysis[]; recommendations: Recommendation[]; reviews: ReviewAction[]; conclusions: HumanConclusion[]; refresh: () => Promise<void> };
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function LegalWorkflowPanel({ caseId, findings, sources, analyses, recommendations, reviews, conclusions, refresh }: Props) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [attest, setAttest] = useState<Record<string, boolean>>({});
  const [humanConclusions, setHumanConclusions] = useState<Record<string, string>>({});
  const [lawyerRecommendations, setLawyerRecommendations] = useState<Record<string, string>>({});
  const [limitations, setLimitations] = useState<Record<string, string>>({});
  const sourceMap = useMemo(() => new Map(sources.map((source) => [source.id, source])), [sources]);
  async function request(path: string, init?: RequestInit) {
    const { data: { session } } = await createClient().auth.getSession();
    if (!session) { location.assign("/signin"); throw new Error("Sign in to continue."); }
    try { return await fetch(`${api}${path}`, { ...init, signal: init?.signal ?? AbortSignal.timeout(90_000), headers: { ...init?.headers, Authorization: `Bearer ${session.access_token}` } }); }
    catch (error) { if (error instanceof DOMException && error.name === "TimeoutError") throw new Error("This request timed out. Check FastAPI and retry."); throw error; }
  }
  async function postJson(path: string, value: unknown, method = "POST") {
    const response = await request(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(typeof body.detail === "string" ? body.detail : "AuraDoc could not save this action."); }
    return response.json();
  }
  async function submitSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError(""); setNotice("");
    const data = new FormData(form);
    try {
      await postJson(`/api/v1/cases/${caseId}/legal-sources`, {
        title: data.get("title"), source_type: data.get("source_type"), authority: data.get("authority"),
        act_or_regulation: data.get("act_or_regulation") || null, section: data.get("section") || null,
        subsection: data.get("subsection") || null, publication_date: data.get("publication_date") || null,
        effective_date: data.get("effective_date") || null, version_label: data.get("version_label") || null,
        official_source_url: data.get("official_source_url"), source_text: data.get("source_text"),
      });
      form.reset(); setNotice("Source evidence recorded as pending human verification."); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "The source could not be recorded."); }
    finally { setBusy(false); }
  }
  async function reviewSource(source: Source, verification_status: "VERIFIED_OFFICIAL" | "REJECTED" | "OUTDATED") {
    setBusy(true); setError(""); setNotice("");
    try {
      await postJson(`/api/v1/cases/${caseId}/legal-sources/${source.id}/review`, {
        verification_status, verification_notes: notes[`source:${source.id}`] ?? "",
        attest_official_source_checked: verification_status === "VERIFIED_OFFICIAL" && Boolean(attest[source.id]),
      });
      setNotice(verification_status === "VERIFIED_OFFICIAL" ? "Human attestation recorded. This confirms the review action and does not determine current legal applicability." : "Source review recorded."); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Source review failed."); }
    finally { setBusy(false); }
  }
  async function analyze(findingId: string) {
    setBusy(true); setError(""); setNotice("");
    try { const response = await request(`/api/v1/cases/${caseId}/findings/${findingId}/legal-analysis`, { method: "POST" });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? "Legal analysis could not be completed."); }
      const result = await response.json(); setNotice(result.status === "NO_VERIFIED_LEGAL_SOURCE_FOUND" ? "No matching verified source was available. Evidence-gap recommendations were saved without legal authority." : "Source-grounded analysis and recommendations saved for human review."); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed."); }
    finally { setBusy(false); }
  }
  async function updateReview(finding: Finding, decision: string) {
    setBusy(true); setError(""); setNotice("");
    try { await postJson(`/api/v1/cases/${caseId}/findings/${finding.id}/review`, { decision, comment: notes[`finding:${finding.id}`] || null }); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Review action failed."); }
    finally { setBusy(false); }
  }
  async function updateRecommendation(item: Recommendation, status: "COMPLETED" | "DISMISSED") {
    setBusy(true); setError("");
    try { await postJson(`/api/v1/cases/${caseId}/recommendations/${item.id}`, { status }, "PATCH"); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Recommendation review failed."); }
    finally { setBusy(false); }
  }
  async function saveHumanConclusion(findingId: string) {
    setBusy(true); setError(""); setNotice("");
    try {
      await postJson(`/api/v1/cases/${caseId}/findings/${findingId}/conclusions`, {
        human_conclusion: humanConclusions[findingId] ?? "",
        lawyer_recommendation: lawyerRecommendations[findingId] ?? "",
        limitations: limitations[findingId] ?? "",
      });
      setNotice("Human conclusion saved with a snapshot of the reviewed finding, evidence, verified sources, and recommendations.");
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Human conclusion could not be saved."); }
    finally { setBusy(false); }
  }

  return <section className="legal-workflow" aria-labelledby="legal-workflow-title">
    <div className="legal-workflow-heading"><div><p className="eyebrow">SOURCE-GROUNDED RESEARCH</p><h2 id="legal-workflow-title">Legal intelligence & next steps</h2><p>Only case-linked source records attested by a human reviewer can be supplied to the AI analysis layer.</p></div><span className="legal-human-only">HUMAN DECISION REQUIRED</span></div>
    {error && <p role="alert" className="form-error">{error}</p>}{notice && <p role="status" className="form-message">{notice}</p>}
    <details className="legal-ingest"><summary>Add source evidence manually</summary><p>Copy source text from an official portal and provide its exact official URL and version/date metadata. New records remain pending until a case owner/reviewer checks the source. AuraDoc does not fetch or independently authenticate portal content.</p>
      <form onSubmit={submitSource}><div className="legal-form-grid"><label>Source title<input name="title" required maxLength={500}/></label><label>Source type<select name="source_type" defaultValue="ACT"><option>ACT</option><option>SECTION</option><option>RULE</option><option>REGULATION</option><option>NOTIFICATION</option><option>ORDER</option><option>JUDGMENT</option><option>OTHER</option></select></label><label>Authority<input name="authority" required maxLength={300} placeholder="Government or court authority"/></label><label>Official source URL<input name="official_source_url" required type="url" placeholder="https://…"/></label><label>Act or regulation<input name="act_or_regulation" maxLength={500}/></label><label>Section<input name="section" maxLength={120}/></label><label>Subsection<input name="subsection" maxLength={120}/></label><label>Version label<input name="version_label" maxLength={300}/></label><label>Publication date<input name="publication_date" type="date"/></label><label>Effective date<input name="effective_date" type="date"/></label><label className="legal-source-text-label">Source text<textarea name="source_text" required minLength={1} maxLength={100000} rows={7}/></label></div><button type="submit" disabled={busy}>Record pending source</button></form>
    </details>
    <section className="legal-source-list"><h3>Case legal-source records</h3>{sources.length ? sources.map((source) => <article className="legal-source-record" key={source.id}><div className="legal-record-top"><div><span className={`legal-verification-badge ${source.verification_status.toLowerCase()}`}>{source.verification_status.replaceAll("_", " ")}</span><h4>{source.title}</h4></div><a href={source.official_source_url} target="_blank" rel="noreferrer">Open official URL ↗</a></div><p className="legal-source-citation">{[source.authority, source.act_or_regulation, source.section && `Section ${source.section}`, source.subsection && `Subsection ${source.subsection}`, source.version_label, source.effective_date && `Effective ${source.effective_date}`].filter(Boolean).join(" · ")}</p><details><summary>Source evidence · SHA-256 {source.source_sha256.slice(0, 16)}…</summary><pre>{source.source_text}</pre></details>{source.verification_status === "PENDING_VERIFICATION" && <div className="legal-review-box"><label>Reviewer notes<textarea rows={2} minLength={20} value={notes[`source:${source.id}`] ?? ""} onChange={(event) => setNotes((old) => ({ ...old, [`source:${source.id}`]: event.target.value }))}/></label><label className="legal-attest"><input type="checkbox" checked={Boolean(attest[source.id])} onChange={(event) => setAttest((old) => ({ ...old, [source.id]: event.target.checked }))}/>I checked the cited text and version at this official source.</label><div className="review-actions"><button disabled={busy || !attest[source.id] || (notes[`source:${source.id}`] ?? "").trim().length < 20} onClick={() => reviewSource(source, "VERIFIED_OFFICIAL")}>Attest source reviewed</button><button disabled={busy || (notes[`source:${source.id}`] ?? "").trim().length < 20} onClick={() => reviewSource(source, "REJECTED")}>Reject source</button></div></div>}{source.verification_status === "VERIFIED_OFFICIAL" && <p className="legal-attestation-note">SOURCE VERIFIED · HUMAN ATTESTED {source.verified_at ? `· ${new Date(source.verified_at).toLocaleString()}` : ""}. Verify current applicability and the relevant case date separately.</p>}</article>) : <p className="empty-state">No legal-source records are attached to this case. Portal links alone are not verified source records.</p>}</section>
    <section className="legal-finding-list"><h3>Finding analysis</h3>{findings.length ? findings.map((finding) => {
      const findingAnalyses = analyses.filter((analysis) => analysis.finding_id === finding.id);
      const findingRecommendations = recommendations.filter((item) => item.finding_id === finding.id);
      const findingReviews = reviews.filter((item) => item.finding_id === finding.id);
      return <article className="legal-finding-work" key={finding.id}><div className="legal-finding-head"><div><span className="finding-status">{finding.relation_type.replaceAll("_", " ")}</span><h4>{finding.summary}</h4><p>{finding.explanation}</p></div><button disabled={busy} onClick={() => analyze(finding.id)}>Analyze verified sources & evidence gaps</button></div>
        {findingAnalyses.map((analysis) => <section className="legal-analysis-result" key={analysis.id}><div className="legal-result-heading"><span>{analysis.status === "NO_VERIFIED_LEGAL_SOURCE_FOUND" ? "NO VERIFIED SOURCE FOUND" : "AI GENERATED · HUMAN REVIEW REQUIRED"}</span><small>{analysis.provider ?? "Provider unavailable"}{analysis.model_name ? ` · ${analysis.model_name}` : ""} · {new Date(analysis.created_at).toLocaleString()}</small></div>
          {analysis.status === "NO_VERIFIED_LEGAL_SOURCE_FOUND" && <p className="legal-no-source">Unable to verify this legal source. Analysis contains no legal authority; recommendations, if any, are evidence-gathering suggestions only.</p>}
          {analysis.legal_relevance.map((item, index) => { const source = sourceMap.get(item.legal_source_id); return <article className="legal-relevance-item" key={`${analysis.id}-${index}`}><span className="legal-source-label">SOURCE VERIFIED · {source?.verification_status === "VERIFIED_OFFICIAL" ? "HUMAN ATTESTED" : "SOURCE UNAVAILABLE"}</span><h5>{source?.title ?? "Source record unavailable"}</h5><p><strong>Why it may matter:</strong> {item.why_may_matter}</p><p><strong>Evidence connection:</strong> {item.evidence_connection}</p><p><strong>Limitations:</strong> {item.limitations}</p>{source && <a href={source.official_source_url} target="_blank" rel="noreferrer">Inspect official source ↗</a>}</article>; })}
          {analysis.missing_evidence.length > 0 && <div className="legal-missing-evidence"><h5>Missing evidence to consider</h5><ul>{analysis.missing_evidence.map((entry, index) => <li key={index}>{entry}</li>)}</ul></div>}
          <p className="legal-analysis-disclaimer">AI analysis is not legal authority or a final decision. Check the original source, version, effective dates, amendments, exceptions and case-date applicability. Human verification is required.</p>
        </section>)}
        {findingRecommendations.length > 0 && <section className="legal-recommendations"><h5>Investigation recommendations</h5>{findingRecommendations.map((item) => <article className="legal-recommendation" key={item.id}><div><span className="legal-priority">{item.priority} PRIORITY · {item.status}</span><strong>{item.action}</strong><p>{item.reason}</p><small>Evidence basis: {item.evidence_basis}</small>{item.legal_source_id && <small>Source: {sourceMap.get(item.legal_source_id)?.title ?? "Linked source record"}</small>}</div>{item.status === "OPEN" && <div className="review-actions"><button disabled={busy} onClick={() => updateRecommendation(item, "COMPLETED")}>Mark reviewed</button><button disabled={busy} onClick={() => updateRecommendation(item, "DISMISSED")}>Dismiss</button></div>}</article>)}</section>}
        <div className="legal-human-review"><h5>Human decision · current finding status: {finding.status.replaceAll("_", " ")}</h5><label>Reviewer notes<textarea rows={2} value={notes[`finding:${finding.id}`] ?? ""} onChange={(event) => setNotes((old) => ({ ...old, [`finding:${finding.id}`]: event.target.value }))}/></label><div className="review-actions"><button disabled={busy} onClick={() => updateReview(finding, "VERIFIED")}>Verify finding</button><button disabled={busy} onClick={() => updateReview(finding, "REJECTED")}>Reject</button><button disabled={busy} onClick={() => updateReview(finding, "REQUEST_MORE_EVIDENCE")}>Request more evidence</button><button disabled={busy} onClick={() => updateReview(finding, "MARK_RESOLVED")}>Mark resolved</button><button disabled={busy} onClick={() => updateReview(finding, "ESCALATE")}>Escalate</button></div>{findingReviews.slice(0, 4).map((review) => <p className="legal-review-history" key={review.id}><time>{new Date(review.reviewed_at).toLocaleString()}</time> · {review.decision.replaceAll("_", " ")} · {review.previous_status ?? "—"} → {review.new_status ?? "—"}{review.reviewer_notes && <span> · {review.reviewer_notes}</span>}</p>)}</div>
        <section className="legal-human-conclusion"><h5>HUMAN CONCLUSION</h5><p>This is authored and saved by the human reviewer. AuraDoc does not fill it from AI output.</p><label>Lawyer / investigator recommendation<textarea rows={2} value={lawyerRecommendations[finding.id] ?? ""} onChange={(event) => setLawyerRecommendations((old) => ({ ...old, [finding.id]: event.target.value }))}/></label><label>Final human conclusion<textarea rows={4} minLength={20} value={humanConclusions[finding.id] ?? ""} onChange={(event) => setHumanConclusions((old) => ({ ...old, [finding.id]: event.target.value }))}/></label><label>Limitations and unresolved evidence gaps<textarea rows={2} value={limitations[finding.id] ?? ""} onChange={(event) => setLimitations((old) => ({ ...old, [finding.id]: event.target.value }))}/></label><button disabled={busy || (humanConclusions[finding.id] ?? "").trim().length < 20} onClick={() => saveHumanConclusion(finding.id)}>Save human conclusion</button>{conclusions.filter((entry) => entry.finding_id === finding.id).map((entry) => <article className="human-conclusion-record" key={entry.id}><strong>HUMAN CONCLUSION · {new Date(entry.created_at).toLocaleString()}</strong><p>{entry.human_conclusion}</p>{entry.lawyer_recommendation && <p><b>Lawyer recommendation:</b> {entry.lawyer_recommendation}</p>}{entry.limitations && <p><b>Limitations:</b> {entry.limitations}</p>}<small>Evidence snapshot: {entry.evidence_snapshot.length} reference(s) · Verified-source snapshot: {entry.verified_sources_snapshot.length} · Recommendation snapshot: {entry.recommendations_snapshot.length}</small></article>)}</section>
      </article>;
    }) : <p className="empty-state">Create an evidence-linked finding before requesting legal context.</p>}</section>
  </section>;
}
