# AuraDoc FastAPI backend

Entrypoint: `app.main:app`. Start locally with `uvicorn app.main:app --reload` from `backend/`. Configure backend-only Supabase public project settings and NVIDIA credentials in `backend/.env`; never put privileged keys or provider secrets in frontend environment files.

## Current workflow

- Supabase Auth bearer token verification and caller-JWT PostgREST/Storage operations preserve database RLS.
- Case endpoints support case listing, creation, retrieval, PDF ingestion, document-only review, Vosk transcription, statement/document comparison, human review and an evidence workspace.
- The legal workflow supports case-scoped source records from approved official hostnames, pending human attestation, source-grounded NVIDIA relevance analysis, evidence-gap recommendations, and audit history. Portal content is user-supplied; AuraDoc does not independently fetch or verify the source.
- `/api/v1/health` checks process availability only; it does not assert database, NVIDIA or ASR readiness.

Apply the migrations in order before using the features they define. The newest document-first/write-guard migration is in the repository but has not been applied to the remote Supabase project in this work session. Configure `NVIDIA_API_KEY` and `NVIDIA_MODEL` before generating AI analysis. Audio processing additionally requires a local, licensed Vosk model configured through `VOSK_MODEL_PATH`.

Run backend tests with `python -m pip install -e ".[test]"` then `python -m pytest -q` from this directory.

For a real recording test, follow [`docs/testing-vosk.md`](../docs/testing-vosk.md). The latest NVIDIA live-request diagnostics and remaining provider limitation are recorded in [`docs/nvidia-provider-validation.md`](../docs/nvidia-provider-validation.md); no successful live inference is currently verified.

For a safe minimal live NVIDIA connectivity/inference check, run `python -m scripts.diagnose_nvidia` from this directory. It deliberately prints only a classified result and generic message, not provider response bodies or credentials.

The diagnostic reports safe response-shape metadata and timing without generated text. For five sequential requests using one connection pool, run `python -m scripts.benchmark_nvidia`; it reports aggregate latency only if all five succeed. Rotate any previously exposed credentials before either live command.
