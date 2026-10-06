# AuraDoc — Data Flow and Role Hierarchy

## 1. Purpose

This document defines how data moves through AuraDoc and who can perform each action.

## 2. Primary data flow

```text
Visitor
  ↓
Landing Page
  ↓
Sign Up / Sign In
  ↓
Authenticated User
  ↓
Create / Open Case
  ↓
Upload Audio + Documents
  ↓
Validate + Hash + Store Originals
  ↓
Processing Queue
  ├── Audio → Local ASR → Timestamped Transcript
  └── Document → Parse/OCR → Clauses/Chunks → Embeddings/Search Index
  ↓
Statement Selection / Automatic Analysis
  ↓
Hybrid Retrieval
  ↓
Reranking
  ↓
Local LLM Comparison
  ↓
Structured Finding
  ↓
Evidence Linking
  ↓
Human Review
  ├── Confirm
  ├── Dismiss
  ├── Request More Evidence
  └── Correct Source/Transcript
  ↓
Audit Trail
  ↓
Report / Export
```

## 3. Detailed audio flow

```text
Audio file
 ↓
MIME/size/security validation
 ↓
SHA-256
 ↓
Immutable original storage
 ↓
ASR provider
 ↓
Timestamped segments
 ↓
Optional diarization
 ↓
Transcript quality metadata
 ↓
PostgreSQL transcript records
 ↓
Search / comparison
```

## 4. Detailed document flow

```text
Document
 ↓
Validation
 ↓
SHA-256
 ↓
Immutable original storage
 ↓
PDF/text extraction
 ↓
OCR if needed
 ↓
Page/section/clause extraction
 ↓
Chunking
 ↓
Embedding + lexical index
 ↓
PostgreSQL metadata
 ↓
Retrieval
```

## 5. Finding flow

```text
Transcript segment
        ↓
Query construction
        ↓
Vector + lexical retrieval
        ↓
Candidate clauses
        ↓
Reranking
        ↓
Comparison model
        ↓
Structured relation
        ↓
Evidence validation
        ↓
Finding record
        ↓
Human review
```

## 6. Evidence provenance

Every finding must be traceable in both directions:

```text
Finding
  ↙       ↘
Audio      Document
  ↓          ↓
timestamp   version/page/clause
  ↓          ↓
transcript  exact source text
```

The reviewer must be able to move from the finding to the original evidence.

## 7. Version-aware flow

Documents may have:

- original version
- amendment
- revised agreement
- superseded version
- effective date
- expiration date

Retrieval must not blindly compare a statement against the newest document.

Where version metadata is incomplete, the finding should state the uncertainty.

## 8. Role hierarchy

### OWNER

Highest case-level authority.

Can:

- create/archive case
- manage members
- upload evidence
- run analysis
- review findings
- export reports
- view audit trail

### INVESTIGATOR

Operational case user.

Can:

- view assigned cases
- upload evidence
- run processing
- inspect transcript
- inspect documents
- review findings
- export permitted reports

### REVIEWER

Verification role.

Can:

- inspect evidence
- play audio
- inspect source pages
- confirm/dismiss findings
- add review comments
- correct review status

### VIEWER

Read-only role.

Can:

- view authorized case data
- inspect permitted findings/reports

Cannot:

- upload evidence
- modify findings
- change permissions

## 9. Role hierarchy diagram

```text
OWNER
  │
  ├── INVESTIGATOR
  │
  ├── REVIEWER
  │
  └── VIEWER
```

This is a permission hierarchy, not necessarily an organizational hierarchy.

## 10. Authorization model

For every protected request:

```text
Authentication
    ↓
Identify user
    ↓
Identify requested resource
    ↓
Check case membership/ownership
    ↓
Check role permission
    ↓
Execute operation
```

Never:

```text
Browser says user_id = X
→ trust browser
→ return data
```

## 11. User database isolation

Each user's workspace must be isolated logically.

Example:

```text
User A
 ├── Case A1
 ├── Case A2
 └── Documents/Recordings/Findings

User B
 ├── Case B1
 └── Documents/Recordings/Findings
```

User A must never retrieve User B's records by guessing UUIDs, changing URLs, manipulating filters, or editing request bodies.

## 12. Frontend data flow

Public:

```text
Landing → Auth
```

Authenticated:

```text
Dashboard
 ↓
Cases
 ↓
Case Workspace
 ├── Recordings
 ├── Documents
 ├── Findings
 └── Audit Log
```

## 13. Case workspace layout

Recommended:

```text
┌──────────────┬───────────────────────────┬──────────────────┐
│ Case Nav     │ Transcript / Audio        │ Source Document  │
│              │                           │                  │
│ Recordings   │ waveform                  │ page preview     │
│ Documents    │ timestamped transcript    │ clause highlight │
│ Findings     │                           │                  │
│ Audit Log    │                           │                  │
├──────────────┴───────────────────────────┴──────────────────┤
│ Evidence-linked finding / reviewer actions                  │
└─────────────────────────────────────────────────────────────┘
```

## 14. API data flow

```text
Next.js
  ↓
Authenticated request
  ↓
FastAPI
  ↓
Auth + authorization
  ↓
Service layer
  ↓
PostgreSQL / object storage / AI service
  ↓
Validated response
  ↓
Next.js UI
```

## 15. Error flow

Errors must be explicit.

Examples:

- unauthorized
- forbidden
- file invalid
- processing failed
- evidence unavailable
- insufficient evidence
- model unavailable
- database failure

Do not convert a failed AI/process job into a fake successful finding.

## 16. Acceptance criteria

- Every protected request performs authorization.
- Roles are enforced server-side.
- Case membership is checked.
- Data cannot cross users/cases.
- Original evidence remains traceable.
- Findings connect audio and document evidence.
- Human decisions are stored separately from AI output.
- Audit logs record consequential actions.
