import Link from "next/link";
import { AuraDocHeader } from "@/components/landing/AuraDocHeader";

const bars = [18, 45, 30, 72, 50, 85, 35, 66, 90, 44, 72, 28, 60, 40, 78, 50, 30, 64, 42, 82, 36, 70, 52, 88];

function WorkbenchPreview() {
  return (
    <div className="hero-workbench" aria-label="Illustrative AuraDoc workbench preview using synthetic data">
      <div className="window-bar"><div className="window-dots" aria-hidden="true"><i /><i /><i /></div><span>DEMO CASE / SAMPLE-01</span><span className="secure-label">SYNTHETIC DATA</span></div>
      <div className="workbench-grid">
        <aside className="case-rail" aria-label="Illustrative case navigation"><div className="rail-logo">AD</div><div className="rail-item active">◫</div><div className="rail-item">◉</div><div className="rail-item">▤</div><div className="rail-item">⌁</div><div className="rail-spacer" /><div className="rail-item">⚙</div></aside>
        <section className="transcript-pane" aria-label="Sample transcript evidence">
          <div className="pane-heading"><div><small>RECORDED STATEMENT · SAMPLE</small><strong>Illustrative Interview · 42:18</strong></div><span className="live-tag">DEMO AUDIO</span></div>
          <div className="waveform" aria-hidden="true">{bars.map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}<b /></div>
          <div className="time-row"><span>04:31.08</span><span>04:32.76</span></div>
          <div className="quote-card"><span className="quote-time">04:32 · SAMPLE</span><p>“The payment was agreed to be completed <mark>within thirty days</mark> of the invoice.”</p><small>Speaker label is illustrative · segment #118</small></div>
        </section>
        <section className="document-pane" aria-label="Sample source document">
          <div className="pane-heading"><div><small>SOURCE DOCUMENT · SAMPLE</small><strong>Illustrative Services Agreement</strong></div><span>PAGE 08 / 24</span></div>
          <div className="document-sheet"><div className="doc-kicker">§ 14.2 · PAYMENT TERMS</div><h3>Payment Schedule</h3><p>Invoices under this illustrative agreement shall be settled no later than <mark>sixty (60) days</mark> from the invoice date.</p><div className="doc-rule" /><p className="muted">Demonstration text · not a real contract</p><div className="source-pin">01 <span>Sample source passage</span></div></div>
          <div className="finding-strip"><span className="finding-icon">!</span><div><small>POSSIBLE DISCREPANCY · EXAMPLE</small><strong>30 days stated · 60 days documented</strong></div><span className="review-label">Human review required</span></div>
        </section>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <>
      <AuraDocHeader />
      <main>
        <section className="hero">
          <div className="hero-copy"><div className="eyebrow"><span className="status-dot" />PRIVATE FORENSIC WORKBENCH</div><h1>Turn spoken statements into <em>traceable evidence.</em></h1><p className="hero-lead">AuraDoc connects recorded testimony with relevant contract language, so investigators can review potential discrepancies with context, provenance, and human judgment.</p><div className="hero-actions"><Link className="button" href="/signup">Request access <span>↗</span></Link><a className="button button-ghost" href="#workflow">See how it works</a></div><div className="hero-note"><span>◈</span> Configurable processing · Evidence-linked findings · Human verification</div></div>
          <WorkbenchPreview />
        </section>
        <section className="trust-band"><span>DESIGNED FOR HIGH-SENSITIVITY REVIEW</span><div><b>LOCAL-FIRST</b><b>PROVENANCE</b><b>CASE ISOLATION</b><b>HUMAN REVIEW</b></div></section>
        <section className="section intro" id="capabilities"><div className="section-label">01 / THE WORKBENCH</div><div className="intro-grid"><h2>Evidence should be <em>connected,</em> not scattered.</h2><div><p>AuraDoc brings audio, transcript, source documents, and findings into a case workspace. Available analyses retain links to the source passages that support them.</p><a className="inline-link" href="#workflow">Explore the workflow <span>→</span></a></div></div></section>
        <section className="capability-grid" aria-label="Capabilities">
          <article className="capability feature-large"><div className="card-number">01</div><div className="feature-icon">◌</div><h3>Audio → Transcript</h3><p>The backend includes local Vosk transcription for supported WAV files, with word-derived timestamps. A configured Vosk model and real recording are required; speaker identity is not inferred.</p><div className="mini-meta">LOCAL VOSK · TIMESTAMPED</div></article>
          <article className="capability"><div className="card-number">02</div><div className="feature-icon">▤</div><h3>Document evidence</h3><p>Text-based PDFs can be extracted into page-referenced sections, hashed, and stored as document versions for evidence review.</p><div className="mini-meta">PAGE · SECTION · SHA-256</div></article>
          <article className="capability dark"><div className="card-number">03</div><div className="feature-icon">⌁</div><h3>Evidence-linked findings</h3><p>Configured AI comparisons can link transcript timestamps and document passages to a structured result that remains subject to human review.</p><div className="mini-meta">SOURCE-GROUNDED · REVIEW REQUIRED</div></article>
          <article className="capability wide"><div className="wide-copy"><div className="card-number">04</div><h3>Built for the reviewer, not the algorithm.</h3><p>AuraDoc supports case-based evidence review. Reviewer decisions are recorded separately from AI analysis in the case audit history.</p></div><div className="review-stack"><div><span>PRODUCT PRINCIPLE</span><b>Evidence before conclusions</b></div><div><span>REVIEW PRINCIPLE</span><b>Human verification required</b></div><div><span>APPLICATION FOUNDATION</span><b>Authenticated cases and review flows</b></div></div></article>
        </section>
        <section className="section workflow" id="workflow"><div className="section-label">02 / HOW IT WORKS</div><div className="workflow-head"><h2>From raw record to <em>reviewable finding.</em></h2><p>The available workflow connects case-scoped evidence, configured processing, and recorded human review. External provider and database behavior still depends on deployment configuration.</p></div><div className="steps"><div className="step"><span>01</span><h3>Ingest</h3><p>Place recordings and source documents within a case access boundary.</p></div><div className="step"><span>02</span><h3>Process</h3><p>Extract text from supported PDFs and timestamps from supported WAV recordings.</p></div><div className="step"><span>03</span><h3>Retrieve</h3><p>Rank source passages with lexical matching and preserve their page metadata.</p></div><div className="step"><span>04</span><h3>Review</h3><p>Inspect evidence, record a human decision, and retain the audit trail.</p></div></div></section>
        <section className="security-section" id="security"><div className="security-copy"><div className="section-label light">03 / CONTROL</div><h2>Privacy is an <em>architecture</em> decision.</h2><p>AuraDoc uses authenticated case access and server-side processing paths. Deployment controls determine where evidence is stored and whether configured AI requests leave the local environment.</p><div className="security-list"><div><span>01</span><b>Configured processing</b><small>Local Vosk is available when its model is installed; NVIDIA analysis requires backend credentials and sends the request to the configured provider.</small></div><div><span>02</span><b>Case-level isolation</b><small>Case access is checked by the API and enforced by database policies, subject to live deployment verification.</small></div><div><span>03</span><b>Provenance by design</b><small>Hashes and source references support traceability; hashes alone do not prove authenticity.</small></div><div><span>04</span><b>Air-gap clarity</b><small>True air-gapped operation requires network isolation and self-hosted dependencies.</small></div></div></div><div className="seal" aria-hidden="true"><div className="seal-ring"><span>AURADOC</span><strong>CONTROLLED<br />REVIEW</strong><small>PRIVATE · TRACEABLE · HUMAN REVIEW</small></div></div></section>
        <section className="section about" id="about"><div className="section-label">04 / ABOUT AURADOC</div><div className="about-grid"><h2>A quieter kind of AI.</h2><div><p>No chatbot theatre. No black-box verdicts.</p><p>AuraDoc is a forensic review workbench designed to make evidence easier to inspect and question. It does not determine truth, guilt, perjury, or legal liability.</p><Link className="inline-link" href="/about">Read the product principles <span>→</span></Link></div></div></section>
        <section className="cta"><div><span className="section-label">PRIVATE FORENSIC REVIEW</span><h2>Bring the evidence.<br /><em>Keep the judgment.</em></h2><p>Create an account or sign in to access the case workspace. Processing and live integrations depend on configured services.</p></div><Link className="button button-light" href="/signup">Request access <span>↗</span></Link></section>
      </main>
      <footer className="footer"><div className="brand footer-brand"><span className="brand-mark"><span /><span /><span /></span><span>Aura<span className="brand-accent">Doc</span></span></div><p>Forensic audio &amp; legal document review.</p><div className="footer-links"><a href="#capabilities">Capabilities</a><a href="#workflow">Workflow</a><a href="#security">Security</a><Link href="/signin">Sign in</Link></div><small>© 2026 AuraDoc. Built for evidence-led review.</small></footer>
    </>
  );
}
