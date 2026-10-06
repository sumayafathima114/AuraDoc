# AuraDoc — Technology Stack Specification

## 1. Purpose

This document defines the implementation stack. It intentionally prioritizes the user's required technologies: **Python, TypeScript and PostgreSQL**.

## 2. Stack summary

| Layer | Technology | Responsibility |
|---|---|---|
| Public/application UI | Next.js + React + TypeScript | Pages, routing, UI, forms |
| Styling | Tailwind CSS and/or CSS modules | Design system and responsive styling |
| Component primitives | Accessible component library or custom primitives | Reusable UI |
| API | Python + FastAPI | Business logic and REST API |
| Validation | Pydantic | Python request/response validation |
| Database | PostgreSQL | System of record |
| ORM/data access | SQLAlchemy or equivalent typed data layer | Persistence |
| Vector search | PostgreSQL + pgvector where appropriate | Semantic retrieval |
| Keyword search | PostgreSQL full-text search / BM25-compatible local service if needed | Lexical retrieval |
| Background jobs | Redis + worker or equivalent | Long-running processing |
| Object storage | Local encrypted storage / MinIO in controlled deployment | Audio/document files |
| ASR | Pluggable local ASR provider | Speech-to-text |
| Embeddings | Pluggable local embedding provider | Semantic indexing |
| Reranker | Optional local reranker | Retrieval quality |
| LLM | Pluggable local LLM runtime | Evidence comparison |
| Document parsing | Python PDF/document tooling | Text extraction |
| OCR | Local OCR provider when required | Scanned documents |
| Testing | Vitest/Jest + Playwright; pytest | Quality assurance |
| API contract | OpenAPI + generated/validated TypeScript types | Frontend/backend compatibility |

## 3. Frontend

### MUST

- TypeScript must be used for application code.
- Use strict typing where practical.
- Use reusable components.
- Keep route-level pages thin.
- Use a consistent design system.
- Implement loading, empty, error and success states.
- Use accessible form labels and keyboard navigation.
- Optimize images using Next.js mechanisms.

### Routes

```text
/
/signin
/signup
/forgot-password
/about
/dashboard
/cases
/cases/[caseId]
```

## 4. UI design system

AuraDoc must look premium, royal, institutional and forensic.

### Palette

```text
Deep Navy      #081724
Slate          #132334
Charcoal       #1F2937
Muted Brass    #B89452
Light Gold     #D9B979
Ivory          #F5F2EB
Paper          #FBFAF7
Line           #D8D3C8
Success        restrained green
Warning        restrained amber
Error          restrained red
```

### Typography

Use a refined serif display face for major headings and a clean sans-serif for interface/body text.

Preferred direction:

- Headings: Playfair Display or comparable editorial serif.
- Body/UI: DM Sans, Inter or comparable neutral sans-serif.

Typography must create hierarchy, not decoration.

### Prohibited visual style

- No 3D animated hero.
- No neon gradients.
- No robot/AI artwork.
- No excessive glassmorphism.
- No floating blobs.
- No excessive rounded cards.
- No chatbot-first landing page.
- No generic “AI-powered” visual clichés.
- No animation that competes with evidence content.

## 5. Landing page implementation

Required structure:

```text
Navbar
  → logo
  → Home
  → Capabilities
  → Workflow
  → Security
  → About
  → Sign In
  → Request Access

Hero
  → concise forensic/legal quote
  → explanation
  → primary CTA
  → secondary CTA
  → product/workbench reference image

Services / Capabilities
  → Audio-to-evidence
  → Contract comparison
  → Evidence-linked findings
  → Local/private processing
  → Human verification

How it works
  01 Upload
  02 Transcribe
  03 Retrieve
  04 Compare
  05 Verify

Security / Control

About

Contact

Footer
```

## 6. Image embedding

For the public landing page:

- Use local image assets in the repository where possible.
- Use `next/image` for raster images.
- Use SVG for logos/icons where practical.
- Give images descriptive `alt` attributes.
- Do not embed copyrighted third-party images without permission.
- Do not upload real legal evidence to an image CDN.
- Product screenshots must use synthetic/demo data.

Example:

```tsx
import Image from "next/image";

<Image
  src="/images/auradoc-workbench.png"
  alt="AuraDoc evidence verification workbench showing transcript and source document side by side"
  width={1400}
  height={900}
  priority
/>
```

## 7. Python backend

Use FastAPI with a layered structure:

```text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    repositories/
    workers/
    ai/
      asr/
      embeddings/
      retrieval/
      reranking/
      llm/
    evidence/
    reports/
    audit/
```

Business logic belongs in services, not route handlers.

## 8. AI provider abstraction

The following interfaces should be defined:

```python
class ASRProvider:
    def transcribe(self, audio_path): ...

class EmbeddingProvider:
    def embed(self, texts): ...

class RerankerProvider:
    def rerank(self, query, candidates): ...

class LLMProvider:
    def compare(self, statement, evidence): ...
```

This prevents model lock-in and makes evaluation possible.

## 9. ASR requirement

The original PRD references Whisper, but the current product specification explicitly removes Whisper.

Therefore:

- Do not import Whisper.
- Do not build the application around Whisper-specific APIs.
- Select a local ASR implementation behind `ASRProvider`.
- Benchmark candidate ASR models for language, accents, numerals, names and timestamps.
- Store provider/model/version metadata with every transcript.

## 10. Retrieval

Preferred flow:

```text
Statement
  ↓
metadata filters
  ↓
vector search + lexical search
  ↓
merge
  ↓
rerank
  ↓
top evidence candidates
```

Do not assume vector similarity equals legal relevance.

## 11. PostgreSQL

Use PostgreSQL for:

- users
- cases
- membership
- recordings metadata
- transcripts
- documents
- versions
- chunks
- findings
- evidence links
- reviews
- reports
- audit logs

Use pgvector if semantic retrieval is kept inside PostgreSQL.

## 12. API contract

Generate or maintain one authoritative OpenAPI schema.

Frontend and backend must agree on:

- endpoint
- HTTP method
- authentication
- request body
- response body
- error format
- pagination
- filtering
- sorting

Do not allow the frontend and backend to invent independent shapes.

## 13. Testing

### Frontend

- unit/component tests
- accessibility checks
- integration tests
- end-to-end tests

### Backend

- service tests
- API tests
- database integration tests
- authorization tests
- AI pipeline tests

### Critical end-to-end workflow

```text
Browser
→ Next.js
→ Python API
→ PostgreSQL / local processing
→ evidence-linked response
→ Next.js
→ human reviewer
```

## 14. Environment configuration

Secrets and deployment configuration must be environment based.

Never hardcode:

- database passwords
- auth secrets
- API keys
- encryption keys
- private model credentials

In air-gapped mode, external API credentials should not be required for core AI processing.

## 15. Acceptance criteria

- Frontend is TypeScript.
- Backend is Python.
- PostgreSQL is the primary database.
- API contract is documented.
- AI providers are replaceable.
- Whisper is absent from the implementation.
- Landing page matches the AuraDoc premium forensic design.
- Image assets are locally controlled and optimized.
- Tests can run independently by layer.
