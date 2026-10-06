# AuraDoc functional audit

Audit date: 6 October 2026. This status records local tests and code inspection separately from live services.

## Status summary

| Area | Status | Evidence and limit |
|---|---|---|
| Next.js application | PARTIAL | TypeScript, lint, and production build pass. No authenticated browser E2E was run. |
| Authentication | PARTIAL | Supabase SSR auth, protected pages, sign-out, signup, password reset, and reset completion are implemented. A PKCE callback was added for signup/reset. Its Supabase redirect allowlist and actual email flows still need live verification. |
| Case API and isolation | PARTIAL | FastAPI derives user identity from the verified bearer token and passes caller JWT to Supabase; migrations define case-membership RLS. API health/unauthenticated rejection were checked locally. Live RLS/two-user access was not tested. |
| PDF extraction | PARTIAL | The fictional PDF fixture parsed locally: one page, payment term extracted, SHA-256 matched, and lexical retrieval found the 60-day passage. Supabase upload/storage/persistence was not exercised. OCR is not implemented. |
| Document versions | PARTIAL | Version tables and hashes exist. Current upload always creates a new document with `v1`; amendment/version continuation and supersession relationships are not implemented. |
| Audio / Vosk | PARTIAL | Configured local model exists and loads. Windows System.Speech exposed installed voices but synthesis stalled; no WAV fixture was produced, so real speech recognition, timestamps, upload, and persistence were not backtested. |
| AI provider | PARTIAL | NVIDIA adapter has schema/evidence-ID validation and mocked tests. No local LLM adapter exists. Live NVIDIA calls were intentionally not made because the previously exposed key has not been rotated. |
| NVIDIA diagnostic | PARTIAL | Smoke request adjusted from 8 tokens/default reasoning to 32 tokens and documented GLM low-effort options; mocked regression test passes. The prior reported HTTP 200 malformed response has no retained body/shape, so the root cause is plausible, not confirmed. |
| Retrieval | PARTIAL | Deterministic lexical ranking is implemented and the local PDF fixture returns the matching passage. No embeddings/vector search/reranker. |
| Legal Intelligence | PARTIAL | User enters source metadata/text from allowlisted official hosts; new sources are pending and require human attestation. India Code and Supreme Court are portal links only. No automated portal ingestion or independent legal-source verification. |
| Recommendations / review / audit | PARTIAL | APIs, human source/finding/recommendation review, and audit triggers are present in code/migrations. No live workflow persistence was tested. Audit lacks explicit PDF/audio ingest/transcription events; history is shown within case workspace, not a separate audit page. |
| Settings/profile | PARTIAL | Display name and local theme work by implementation. Notifications, retention, profile image/organization/jurisdiction fields are not implemented. |

## Validation performed

- Backend: `python -m pytest -q` — **59 passed**, one pytest cache-path warning.
- Frontend: `npm run typecheck` — pass; `npm run lint` — pass; `npm run build` — pass (14 routes generated, including `/auth/callback`).
- FastAPI: import/OpenAPI lists 20 endpoints; local `/api/v1/health` returned 200; protected `/me`, `/dashboard`, `/cases`, `/profile`, and `/legal-sources` returned 401 without credentials.
- Vosk: local model loaded successfully. No transcript was produced because the TTS fixture-generation attempt stalled before creating a WAV.
- PDF: actual fictional fixture parsed and ranked locally; no database write occurred.
- Supabase: local SQL defines three ordered migrations. `npx supabase migration list --linked` failed with a transport error while initializing the login role. Remote migration history/schema/RLS and persistence are therefore NOT VERIFIED in this audit.
- NVIDIA: no live test/benchmark was run. The supplied earlier result (HTTP 200, 4,873 ms, malformed) is historical user-reported evidence, not re-executed.
- Browser: no signed-in browser account/session available; protected and mutation workflows are NOT VERIFIED in a real browser.

## Required before a faculty demo

1. Rotate the exposed NVIDIA key and Supabase database password; update only local `backend/.env` with the replacement values.
2. Add local/deployed `/auth/callback` URLs to Supabase Auth redirect allowlists; confirm Auth email delivery is configured.
3. With rotated credentials, verify Supabase migration history, evidence bucket, database schema, and actual case/PDF persistence; run a two-user RLS test.
4. Run the NVIDIA smoke test, structured comparison, and five-request benchmark. Do not describe the model as working or under five seconds until those live requests pass.
5. Obtain/record real WAV speech or use a working local speech synthesis tool, then test Vosk transcription and persisted transcript provenance.
6. Backtest a real authenticated case through PDF/document review, legal source attestation, analysis, recommendation review, and audit history.

AuraDoc is **PARTIALLY READY** as an application foundation, but not verified as a full end-to-end forensic/legal workflow. It is not a legal authority or decision-maker.
