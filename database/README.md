# AuraDoc database

Supabase/PostgreSQL is the authoritative relational store. Ordered migrations are in [`supabase/migrations`](../supabase/migrations/).

## Migration order

1. `20261004000100_auradoc_mvp.sql` — cases, memberships, documents, recordings, transcript segments, findings, evidence, reviews, audit events, RLS, and ingestion/registration functions.
2. `20261005000100_legal_intelligence_workflow.sql` — case-linked legal-source records, legal analyses, recommendations, review lifecycle, RLS, and audit functions.
3. `20261006000100_document_first_review_and_legal_write_guard.sql` — document-only evidence review support and restriction of direct legal-analysis table inserts in favor of a validating registration RPC.

Apply migrations with the linked Supabase CLI workflow after reviewing the target project and migration history. Do not rerun the one-time foundation migration or reset a production database. The third migration has been added to the repository but has **not** been applied or verified against the live project in this work session.

Case-scoped reads and writes use the authenticated user JWT and database RLS. Backend authorization checks provide clear early denial; database policies and registration functions remain the persistence boundary. Never put private database URLs, service-role keys, or provider secrets in frontend configuration or version control.

The schema stores extracted document page/section evidence with source hashes. A hash supports byte comparison with the recorded digest; it does not establish authenticity or legal validity. OCR for scanned PDFs is not currently implemented.
