# AuraDoc Reference Specification Package

This package contains six implementation-reference Markdown documents for AuraDoc.

## Files

1. `01-system-architecture.md` — overall architecture, API boundary, processing pipeline and page structure.
2. `02-schema-design.md` — PostgreSQL entities, relationships, evidence provenance and user isolation.
3. `03-tech-stack-specification.md` — Python, TypeScript, PostgreSQL and supporting technologies, including UI/image rules.
4. `04-module-logical-instructions.md` — module-by-module coding instructions and acceptance rules.
5. `05-data-flow-and-role-hierarchy.md` — end-to-end data flow, roles, permissions and case isolation.
6. `06-guardrails-and-limitations.md` — AI, legal, privacy, security, evidence and UI guardrails.

## Authority rules

These documents reflect the current project direction:

- Python backend
- TypeScript/Next.js frontend
- PostgreSQL database
- API-based frontend/backend integration
- user-specific/case-level data isolation
- local/private AI processing architecture
- Whisper removed from the implementation
- premium legal/forensic UI
- no 3D animated or generic AI-startup visual style

The original PRD contains older references to Whisper, MiniLM, ChromaDB and Streamlit. Those are treated as historical design context where they conflict with the current requirements. The current six-document specification is authoritative for implementation.

## Suggested project structure

```text
auradoc/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   │   └── images/
│   └── styles/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── repositories/
│       ├── workers/
│       ├── ai/
│       ├── evidence/
│       ├── reports/
│       └── audit/
├── database/
│   └── migrations/
├── tests/
├── docs/
└── reference/
    └── auradoc-reference-docs/
```

## LLM implementation instruction

The coding agent should read all six documents before making architecture-level changes.

Required behavior:

`INSPECT → PLAN → IMPLEMENT → TEST → INTEGRATE → VERIFY`

Do not stop after producing a plan. Do not mark work complete merely because files exist or the UI renders.
