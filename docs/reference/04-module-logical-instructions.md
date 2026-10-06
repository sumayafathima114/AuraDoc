# AuraDoc — Module Logical Instructions

## 1. Purpose

This document tells a coding LLM what each AuraDoc module must do and how modules interact.

## 2. Implementation order

Use this dependency-aware sequence:

```text
1. Project foundation
2. PostgreSQL schema + migrations
3. Authentication + authorization
4. Python API contract
5. Case management
6. File/evidence ingestion
7. Audio transcription adapter
8. Document extraction/OCR
9. Retrieval/indexing
10. Comparison engine
11. Evidence/finding workflow
12. Reports/audit logs
13. Next.js UI
14. Landing/auth/about pages
15. Integration tests
16. Security audit
17. Final validation
```

## 3. Module: Authentication

### Responsibilities

- Sign up
- Sign in
- Sign out
- Forgot/reset password
- Session validation
- Current-user retrieval

### Rules

- Never trust a client-provided user ID.
- Backend must derive identity from authenticated session/token.
- Password handling should be delegated to a secure auth provider or well-tested authentication layer.
- Do not store raw passwords.

## 4. Module: User and authorization

Responsibilities:

- identify current user
- determine case membership
- enforce role permissions
- isolate user data

Permission examples:

| Action | Owner | Investigator | Reviewer | Viewer |
|---|---:|---:|---:|---:|
| View case | ✓ | ✓ | ✓ | ✓ |
| Upload evidence | ✓ | ✓ | optional | — |
| Run analysis | ✓ | ✓ | optional | — |
| Verify finding | ✓ | optional | ✓ | — |
| Dismiss finding | ✓ | optional | ✓ | — |
| Export report | ✓ | ✓ | ✓ | optional |
| Manage members | ✓ | — | — | — |

Exact permissions can be adjusted, but must be explicit.

## 5. Module: Case management

Responsibilities:

- create case
- list cases
- search/filter cases
- open case
- archive case
- manage members

Case dashboard should show:

- case number
- title
- status
- documents
- recordings
- findings
- last activity

## 6. Module: Evidence ingestion

Responsibilities:

- validate upload
- calculate SHA-256
- store original
- create metadata record
- queue processing
- expose processing state

Processing states:

`UPLOADED → VALIDATING → PROCESSING → READY → FAILED`

Never replace the original file with a processed derivative.

## 7. Module: Audio processing

Responsibilities:

- audio validation
- duration extraction
- local ASR
- timestamps
- optional speaker diarization
- transcript storage
- transcript quality metadata

### Important

Do not use Whisper. Implement through the `ASRProvider` abstraction.

Transcript UI must allow the reviewer to:

- play audio
- jump to timestamp
- inspect segment
- edit transcript when authorized
- identify uncertainty

A user edit must be recorded as a change and must not silently overwrite the original machine transcript.

## 8. Module: Document processing

Responsibilities:

- parse PDF/document
- preserve page numbers
- detect headings/clauses
- OCR scanned documents
- create normalized text
- create searchable chunks
- create embeddings

Each chunk must retain:

```text
case_id
document_id
document_version_id
page_number
section_label
clause_label
paragraph_index
content_hash
```

## 9. Module: Retrieval engine

Responsibilities:

1. normalize query
2. apply case/document filters
3. run semantic search
4. run lexical search
5. merge results
6. rerank if enabled
7. return evidence candidates

Output must include source metadata.

Example:

```json
{
  "document_version_id": "...",
  "page": 8,
  "clause": "14.2",
  "text": "Payment shall be completed within 60 days...",
  "retrieval_score": 0.91
}
```

## 10. Module: Comparison engine

The engine compares a spoken statement with retrieved evidence.

### Required reasoning inputs

- exact transcript text
- timestamp
- speaker if available
- source clause text
- page/clause metadata
- document version/effective dates
- definitions and exceptions when available

### Output schema

```json
{
  "relation": "POSSIBLE_DISCREPANCY",
  "summary": "Spoken term differs from source clause",
  "statement_quote": "Payment will be completed within 30 days.",
  "source_quote": "Payment shall be completed within 60 days.",
  "evidence_ids": ["...", "..."],
  "needs_human_review": true,
  "uncertainties": ["ASR accuracy should be checked"]
}
```

The model must return `INSUFFICIENT_EVIDENCE` when evidence is inadequate.

## 11. Module: Finding service

Responsibilities:

- persist AI finding
- attach evidence
- expose finding details
- accept human decision
- preserve review history

Never delete an AI finding after dismissal. Mark it dismissed/superseded and retain the audit trail.

## 12. Module: Human verification

UI should provide:

```text
Finding
 ├── spoken evidence
 │    └── Play at 00:04:32
 ├── source evidence
 │    └── Open page 8 / §14.2
 ├── AI assessment
 ├── uncertainty
 └── reviewer action
      ├── Confirm
      ├── Dismiss
      ├── Need more evidence
      └── Correct transcript/source
```

## 13. Module: Audit trail

Record:

- sign-in/security events where appropriate
- case creation
- upload
- processing
- transcript edits
- finding creation
- review decision
- report generation
- permission changes

Do not log raw sensitive evidence unnecessarily.

## 14. Module: Reporting

Report should contain:

- case information
- source file identifiers
- processing/model metadata
- findings
- exact evidence references
- human review state
- audit metadata

Reports must distinguish:

`AI-generated assessment` from `human-verified conclusion`.

## 15. Module: Landing page

The landing page is a public product introduction, not an application dashboard.

Required sections:

### Navbar

Brand + navigation + sign in + request access.

### Hero

Use a strong quote such as:

> “Turn spoken statements into traceable evidence.”

Do not use exaggerated claims such as “AI that detects lies.”

Hero must contain a real-looking synthetic AuraDoc workbench reference image.

### Services/features

- Audio-to-transcript evidence linking
- Contract/document comparison
- Hybrid evidence retrieval
- Evidence-linked findings
- Human verification
- Local/privacy-first processing

### How services work

`Upload → Process → Retrieve → Compare → Verify → Report`

### Footer

- AuraDoc brand
- concise product statement
- About
- Contact
- privacy/security statement
- copyright

## 16. Module: Authentication UI

Create separate routes for:

- Sign in
- Sign up
- Forgot password

Maintain the same visual language as the landing page.

Do not create a generic purple-gradient SaaS authentication screen.

## 17. Module: About

The About page should explain:

- what AuraDoc is
- why evidence traceability matters
- privacy-first philosophy
- human verification
- intended users
- limitations

Avoid unsupported claims of legal authority or autonomous legal judgment.

## 18. Module: UI component library

Create reusable components for:

- Navbar
- Sidebar
- Buttons
- Inputs
- Selects
- Cards
- Status badges
- Tables
- Tabs
- Modal/drawer
- Audio player
- Transcript segment
- Document viewer
- Finding card
- Evidence card
- Timeline
- Empty state
- Loading state
- Error state
- Toast/notification

## 19. UI visual rules

Premium/royal does NOT mean flashy.

Use:

- deep navy
- warm ivory
- muted brass
- editorial serif typography
- clean sans-serif UI text
- thin borders
- controlled shadows
- strong whitespace
- precise alignment

Do not use:

- 3D animations
- neon
- floating blobs
- AI robots
- excessive glassmorphism
- over-animated cards
- generic chatbot UI

## 20. Module completion rule

A module is complete only when it is:

`IMPLEMENTED + INTEGRATED + TESTED + VERIFIED`

A file existing on disk is not evidence of completion.
