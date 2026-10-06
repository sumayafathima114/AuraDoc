# AuraDoc application architecture

```text
Browser → Next.js / TypeScript → FastAPI / Python → Supabase / PostgreSQL
                                               └→ NVIDIA API (backend only)
                                               └→ local Vosk ASR
```

## Ownership boundaries

- Next.js owns presentation, routes, session-aware UI, and browser interactions.
- FastAPI owns authorization-sensitive business logic, PDF parsing, Vosk orchestration, retrieval, NVIDIA calls, legal workflow, findings, review, and reports.
- Supabase Auth identifies the user. FastAPI validates the bearer token and uses the caller-scoped JWT for PostgREST/Storage requests. PostgreSQL RLS is the final data authorization boundary.
- Originals and derived evidence are stored separately with SHA-256 integrity identifiers and page/timestamp provenance.

## Implemented API areas

The FastAPI `/api/v1` API includes health, profile, dashboard, case CRUD, case workspace, PDF ingestion, WAV ingestion/transcription, statement/document comparison, finding review, legal-source intake/review, legal relevance analysis, and recommendation status updates. OpenAPI at `/openapi.json` is the route contract. The health endpoint reports process status only.

The workspace currently supports document upload and optional WAV transcription. Statement/document comparison requires persisted transcript and document evidence. Live NVIDIA inference and authenticated full-workflow persistence remain unverified; see [MVP status](mvp-status.md).

## Database

Apply migrations in order for a new database:

1. `supabase/migrations/20261004000100_auradoc_mvp.sql`
2. `supabase/migrations/20261005000100_legal_intelligence_workflow.sql`

The migrations define case membership, evidence, transcripts, findings, reviews, audit records, legal sources, analyses, and recommendations with RLS and database-side registration checks. Do not create duplicate tables or bypass RLS with a service-role client.

## Processing boundaries and limitations

- PDF extraction is for text-bearing PDFs; OCR for scanned documents is not implemented.
- The current ASR provider is local Vosk; accepted audio is uncompressed mono 16-bit PCM WAV, 8–48 kHz. Whisper is not used.
- NVIDIA credentials stay in the backend environment. Model output is schema-validated and evidence references are restricted to supplied records, but live model behavior still requires validation.
- Legal portal links are not imported sources. Legal-source text is manually entered, source status is subject to human attestation, and AuraDoc does not independently prove legal validity or current applicability.
- Audio/document ingestion events are not yet a complete audit chronology; review and legal workflow events have database audit support.
- Local processing is not equivalent to air-gapped deployment. Air-gapped operation requires network isolation and self-hosted infrastructure.
