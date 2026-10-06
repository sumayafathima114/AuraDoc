# AuraDoc — System Architecture Reference

## 1. Purpose

This document is the authoritative architecture reference for building AuraDoc, a privacy-focused forensic audio and legal-document verification workbench.

AuraDoc links statements from recorded interviews/depositions/witness sessions to relevant clauses in contracts or other source documents, identifies possible discrepancies, and presents traceable evidence for human review.

This document is intended to be passed to an LLM/coding agent as an implementation specification.

## 2. Product principle

AuraDoc is a **decision-support and evidence-navigation system**, not an autonomous lawyer, lie detector, judge, or legal decision maker.

The core product loop is:

`User → Case → Audio/Documents → Processing → Retrieval → Comparison → Evidence-linked Finding → Human Verification → Audit/Report`

## 3. Architecture style

Use a modular full-stack architecture:

```text
┌───────────────────────────────────────────────────────────────┐
│                       NEXT.JS FRONTEND                        │
│                     TypeScript / React                        │
│                                                               │
│ Landing │ Auth │ Dashboard │ Cases │ Workspace │ About       │
└──────────────────────────────┬────────────────────────────────┘
                               │ HTTPS / JSON API
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                     PYTHON API / SERVICES                     │
│                         FastAPI                               │
│                                                               │
│ Auth Context │ Case Service │ Ingestion │ ASR │ Retrieval     │
│ Comparison   │ Evidence    │ Reports    │ Audit │ Jobs        │
└──────────────┬──────────────────────────────┬─────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────┐      ┌─────────────────────────────┐
│      PostgreSQL         │      │ Local AI / Processing       │
│ users, cases, docs,     │      │ ASR, embeddings, reranker,  │
│ recordings, findings,   │      │ local LLM, OCR/parsing      │
│ evidence, audit logs    │      └─────────────────────────────┘
└─────────────────────────┘
               │
               ▼
┌───────────────────────────────────────────────────────────────┐
│ Local / controlled object storage                              │
│ original audio │ original documents │ derived artifacts       │
└───────────────────────────────────────────────────────────────┘
```

## 4. Mandatory architectural decisions

### MUST

- Frontend: Next.js + TypeScript.
- Backend: Python + FastAPI.
- Primary database: PostgreSQL.
- Maintain a strict API contract between frontend and Python backend.
- Keep business logic in the Python backend.
- Enforce user/case authorization server-side.
- Store original evidence separately from derived/transformed data.
- Preserve provenance for every AI-generated finding.
- Keep AI inference pluggable so ASR/LLM/embedding models can be replaced without rewriting the application.
- Support local/on-premise processing as the target privacy architecture.
- Keep human verification as a required workflow for consequential findings.

### MUST NOT

- Do not use Whisper because the current project direction explicitly removes it.
- Do not send sensitive audio, transcripts, contracts, embeddings, or findings to an unapproved cloud AI API in local/air-gapped mode.
- Do not let the frontend decide authorization.
- Do not allow one user's case data to appear in another user's workspace.
- Do not present an AI finding as a final legal conclusion.
- Do not replace real workflows with fake buttons or placeholder success messages.

## 5. Processing pipeline

### 5.1 Case creation

1. Authenticated user creates a case.
2. Backend assigns a case ID.
3. Case is owned by the authenticated user/authorized organization.
4. All subsequent uploads are associated with the case.

### 5.2 Audio processing

1. User uploads an approved audio file.
2. Backend validates file type, size, checksum and ownership.
3. Original audio is stored immutably.
4. A local ASR adapter creates timestamped transcript segments.
5. Optional speaker diarization assigns speaker labels.
6. Transcript quality metadata is stored.
7. Transcript segments become searchable evidence objects.

The ASR implementation must be provider/model agnostic. The system must expose an `ASRProvider` interface rather than coupling the application to one model.

### 5.3 Document processing

1. User uploads PDF/document.
2. Original file is hashed and stored.
3. Text is extracted.
4. OCR is applied when required.
5. Pages, paragraphs, headings and clauses are identified where possible.
6. Chunks are generated while retaining document/page/clause provenance.
7. Embeddings and keyword-search representations are generated locally.

### 5.4 Retrieval

Use hybrid retrieval:

`semantic vector retrieval + keyword/BM25 retrieval + metadata filtering + optional reranking`

Retrieval must return source identifiers, not only text.

### 5.5 Comparison

The comparison service receives:

- transcript statement
- timestamp
- speaker if available
- retrieved clause(s)
- document/page/clause metadata
- relevant case metadata
- applicable comparison rules

The model returns structured JSON, not uncontrolled prose.

### 5.6 Finding creation

A finding must contain:

- relation/status
- transcript evidence reference
- document evidence reference
- quoted source text
- explanation
- model metadata
- retrieval metadata
- uncertainty/quality indicators
- human verification state

Recommended relation values:

- `CONSISTENT`
- `POSSIBLE_DISCREPANCY`
- `CONDITIONAL`
- `TEMPORAL_OR_VERSION_MISMATCH`
- `DEFINITION_OR_EXCEPTION_MISMATCH`
- `INSUFFICIENT_EVIDENCE`
- `NEEDS_HUMAN_REVIEW`

## 6. API boundary

The frontend communicates with the Python API through documented REST endpoints.

Representative endpoints:

```text
POST   /api/v1/auth/session
GET    /api/v1/me
GET    /api/v1/cases
POST   /api/v1/cases
GET    /api/v1/cases/{case_id}
POST   /api/v1/cases/{case_id}/recordings
POST   /api/v1/cases/{case_id}/documents
GET    /api/v1/cases/{case_id}/transcripts
GET    /api/v1/cases/{case_id}/findings
POST   /api/v1/findings/{finding_id}/verify
POST   /api/v1/findings/{finding_id}/dismiss
GET    /api/v1/cases/{case_id}/audit-log
POST   /api/v1/cases/{case_id}/reports
GET    /api/v1/health
```

Exact endpoint naming may be adjusted during implementation, but the contract must remain documented and versioned.

## 7. Frontend architecture

Recommended structure:

```text
frontend/
  app/
    page.tsx
    signin/page.tsx
    signup/page.tsx
    forgot-password/page.tsx
    about/page.tsx
    dashboard/page.tsx
    cases/page.tsx
    cases/[caseId]/page.tsx
  components/
    navigation/
    auth/
    cases/
    evidence/
    audio/
    documents/
    findings/
    audit/
    ui/
  lib/
    api/
    auth/
    validation/
  styles/
```

## 8. Landing page architecture

The public landing page must contain:

1. Navigation bar
2. Hero quote/value proposition
3. Product/workbench reference image
4. Services/capabilities
5. How AuraDoc works
6. Privacy/security section
7. Human-verification section
8. About/product philosophy
9. Contact information
10. Footer

Image embedding requirements:

- Use optimized local/static assets for product screenshots and reference imagery.
- Use Next.js image optimization where appropriate.
- Provide meaningful `alt` text.
- Do not embed remote AI image URLs in a true offline deployment.
- Never send confidential case data to an external image service.
- Marketing imagery and product screenshots must never contain real confidential evidence.

## 9. Authentication pages

Required public routes:

- `/signin`
- `/signup`
- `/forgot-password`

Authentication UI must have:

- validation
- loading state
- server error state
- accessible labels
- password visibility control where appropriate
- session handling
- redirect after successful authentication

## 10. Internal user database isolation

The application must logically isolate every user's data.

At minimum:

`User → Cases → Recordings/Documents/Findings/Evidence/Audit Logs`

Every protected query must be scoped to authenticated identity and authorized case membership.

Do not accept a browser-supplied `user_id` as an authorization decision.

## 11. Non-functional requirements

- Responsive desktop/tablet/mobile UI.
- Accessible forms and keyboard navigation.
- Clear loading/error/empty/success states.
- Structured backend logging.
- Audit logging for security-sensitive actions.
- Deterministic model/configuration metadata for reproducibility.
- Testable service boundaries.

## 12. Acceptance criteria

The architecture is accepted only if:

- Next.js/TypeScript can call the Python API.
- Python can safely read/write PostgreSQL data.
- An authenticated user can create a case.
- A user cannot access another user's case by changing an ID in a request.
- Audio and documents retain source provenance.
- Findings link back to timestamp and page/clause evidence.
- Human verification is represented explicitly.
- Local/offline processing can be configured without hidden external AI calls.
- The landing page uses the defined premium legal/forensic design system.
