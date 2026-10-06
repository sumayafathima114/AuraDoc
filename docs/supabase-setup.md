# Connect AuraDoc to Supabase

## Frontend Auth configuration

1. In the Supabase project API settings, copy the project URL and publishable key (or legacy `anon` key). Never use a `service_role` or secret key in the frontend.
2. Copy `frontend/.env.local.example` to `frontend/.env.local` and set:

   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_OR_ANON_KEY
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Restart Next.js after saving. Set the local Auth site URL to `http://localhost:3000` and allow `http://localhost:3000/auth/callback` in Auth redirect URLs. For deployment, add the matching deployed `/auth/callback` URL. Signup confirmation and password reset use this PKCE callback to exchange the one-time code before continuing. Email confirmation/reset delivery still depends on Supabase Auth email configuration.

## Backend and database

- Keep `SUPABASE_DB_URL`, NVIDIA credentials, and any database password only in `backend/.env`. Never copy them into frontend variables, documentation, source control, or chat.
- If the database password previously shared in development is still active, rotate it in the Supabase Dashboard and update the private backend configuration. Prefer the Session Pooler for environments that cannot reach the direct IPv6 database host.
- Local migrations, in order, are `supabase/migrations/20261004000100_auradoc_mvp.sql`, `supabase/migrations/20261005000100_legal_intelligence_workflow.sql`, and `supabase/migrations/20261006000100_document_first_review_and_legal_write_guard.sql`. The latest audit could not verify remote migration history: the linked CLI failed while initializing its database login role. Do not infer remote schema status from the local files.
- For a new Supabase project, review migration history and apply the migrations in order using the Supabase CLI linked-project workflow. Review the dry run before applying. Do not reset production or pass a database URL/password as a command-line argument; command arguments may be visible to local process inspection. Never manually duplicate tables or disable RLS.
- Verify the project’s migration history, table definitions, RLS policies, and triggers after applying. `/api/v1/health` only confirms FastAPI process health; it is not a database readiness check.

## Source review lifecycle

AuraDoc can record legal-source metadata/text entered from an allowed official HTTPS portal. New source records are pending review. An authorized case owner/reviewer records human attestation before the source can be considered by legal analysis. This is not independent or cryptographic authentication and does not guarantee current applicability. Portal links alone are not verified AuraDoc sources.

Legal analysis uses only case-linked records marked `VERIFIED_OFFICIAL`; when none are available, the system returns a no-verified-source state. The model is not an authority on law and must not supply missing citations.

## Local commands

Start the backend from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Start the frontend from `frontend/`:

```powershell
npm run dev
```

Frontend configuration contains only public Supabase settings and the API URL. FastAPI validates the user session and uses caller-scoped access so database RLS remains active.
