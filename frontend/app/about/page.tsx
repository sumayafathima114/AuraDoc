import Link from "next/link";
import { AuraDocHeader } from "@/components/landing/AuraDocHeader";

export default function AboutPage() {
  return (
    <>
      <AuraDocHeader />
      <main className="section about-page">
        <div className="section-label">ABOUT AURADOC</div>
        <h1>A quieter kind of AI.</h1>
        <div className="about-copy">
          <p>AuraDoc is designed as a forensic audio and legal-document review workbench. Its purpose is to help authorized reviewers navigate statements, source documents, versions, and evidence references in one controlled case workspace.</p>
          <h2>Evidence first. Human judgment always.</h2>
          <p>Potential findings should point to their source audio, timestamp, transcript passage, document version, page, and clause. Reviewers remain responsible for interpreting context and recording decisions.</p>
          <p>AuraDoc is not a lie detector, guilt detector, perjury detector, or autonomous legal decision-maker. A hash can support byte-integrity checks; it cannot establish authenticity or truth.</p>
          <Link className="inline-link" href="/">Return to the landing page <span>→</span></Link>
        </div>
      </main>
    </>
  );
}
