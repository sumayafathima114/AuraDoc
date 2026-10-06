# AuraDoc

AuraDoc is an evidence-linked forensic and legal review workbench. It helps authorized users organize case evidence, extract text from legal PDFs, optionally transcribe WAV recordings with local Vosk, compare evidence through a configured NVIDIA provider, and route findings for human review. It does not determine truth, guilt, perjury, breach, or legal liability.

## Current implementation

- **Frontend:** Next.js App Router, React, TypeScript, Supabase Auth SSR, premium legal/forensic UI.
- **Backend:** FastAPI owns case, evidence, comparison, legal-source, recommendation, and review operations.
- **Database:** Supabase/PostgreSQL migrations with caller-scoped JWT access and RLS.
- **PDF:** text-based PDF extraction, page-level sections, and SHA-256 tracking. Scanned PDFs/OCR are not supported.
- **Audio:** optional mono 16-bit PCM WAV transcription through the local Vosk model. No Whisper fallback.
- **AI:** backend-only NVIDIA adapter with structured-output/evidence-reference checks. Live inference has timed out in recorded validation; no inference result is claimed.
- **Legal sources:** external portal links are references only. Legal-source records are manually supplied and require human attestation; AuraDoc does not independently authenticate the law or check current applicability.

Document-first AI review and statement comparison are now separate workflows; both require stored, page-referenced PDF evidence, and document-only review is explicitly marked as requiring human review. The additive migration for this path and legal-analysis write hardening is in the repository but has **not** been applied to the live Supabase project. A complete authenticated runtime journey has **not** been verified. See [MVP status](docs/mvp-status.md), [Vosk test procedure](docs/testing-vosk.md), and [NVIDIA diagnostics](docs/nvidia-provider-validation.md).

## Local setup

Requirements: Node.js 20.9+, Python 3.10+, configured Supabase project, backend environment, and the local Vosk model for audio transcription.

1. For a new Supabase project, apply the SQL migrations in order:
   - `supabase/migrations/20261004000100_auradoc_mvp.sql`
   - `supabase/migrations/20261005000100_legal_intelligence_workflow.sql`
   - `supabase/migrations/20261006000100_document_first_review_and_legal_write_guard.sql`
   For the existing AuraDoc project, check migration history and apply only migrations that are actually pending; never rerun the foundation migrations.
2. Configure `frontend/.env.local` using `frontend/.env.local.example` (public Supabase URL/key and API URL only).
3. Configure `backend/.env` using `backend/.env.example`. Keep NVIDIA credentials and database connection credentials backend-only.

### Terminal 1 — FastAPI

```powershell
cd "D:\mini project\AuraDoc\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API health endpoint is `http://localhost:8000/api/v1/health`. It checks process availability only, not database, NVIDIA, or Vosk readiness.

### Terminal 2 — Next.js

```powershell
cd "D:\mini project\AuraDoc\frontend"
npm install
npm run dev
```

Open `http://localhost:3000`. Sign up/sign in through Supabase Auth. For a new account, Supabase email confirmation settings apply.

## Validation

Backend tests:

```powershell
cd "D:\mini project\AuraDoc\backend"
python -m pytest -q
```

Frontend checks:

```powershell
cd "D:\mini project\AuraDoc\frontend"
npm run typecheck
npm run lint
npm run build
```

## Security and product limits

- Never put `NVIDIA_API_KEY`, `SUPABASE_DB_URL`, or a Supabase service-role key in frontend environment variables.
- FastAPI forwards the authenticated caller context; PostgreSQL RLS remains the authorization boundary.
- Uploaded PDFs and transcripts are untrusted evidence, not instructions for the model.
- SHA-256 supports byte-integrity comparison; it does not prove authenticity or truth.
- A finding is an AI-assisted review candidate. Human review remains necessary.
- A source marked by human attestation is not cryptographically or independently authenticated by AuraDoc.
- True air-gapped operation requires network isolation and self-hosted dependencies; local model use alone does not make a deployment air-gapped.

The original static landing-page files remain preserved at the repository root and in `reference/landing-page/`; supplied UI references are under `frontend/public/images/`.
