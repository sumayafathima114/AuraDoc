# AuraDoc — PostgreSQL Schema Design Reference

## 1. Purpose

This document defines the logical PostgreSQL data model for AuraDoc.

The database must support user isolation, case management, evidence provenance, AI processing, human verification and auditability.

## 2. Design principles

### MUST

- Use PostgreSQL as the system of record.
- Use UUID primary keys for application entities.
- Use foreign keys for relationships.
- Add `created_at` and `updated_at` where mutable records exist.
- Store ownership explicitly.
- Use transactions for multi-table state changes.
- Use indexes based on actual query patterns.
- Preserve immutable original evidence metadata.
- Version documents because amendments/revisions can change meaning.

### MUST NOT

- Do not store all application data in one unstructured JSON column.
- Do not trust client-provided user IDs.
- Do not overwrite original evidence when a processed derivative is created.
- Do not delete evidence merely because an AI finding was dismissed.

## 3. Entity relationship overview

```text
users
  │
  ├── user_profiles
  │
  └── cases
        │
        ├── case_members
        ├── recordings
        │      └── transcript_segments
        │
        ├── documents
        │      └── document_versions
        │             └── document_chunks
        │
        ├── findings
        │      ├── finding_evidence
        │      └── finding_reviews
        │
        ├── reports
        └── audit_logs
```

## 4. Core tables

### 4.1 users

Authentication identity. If an external auth provider is used, store its stable subject ID rather than duplicating passwords.

Fields:

```text
id UUID PK
external_auth_id TEXT UNIQUE
email CITEXT UNIQUE
status TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
last_login_at TIMESTAMPTZ NULL
```

### 4.2 user_profiles

```text
user_id UUID PK/FK users.id
full_name TEXT
organization_name TEXT NULL
job_title TEXT NULL
preferences JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### 4.3 cases

```text
id UUID PK
owner_user_id UUID FK users.id
case_number TEXT UNIQUE
name TEXT
description TEXT NULL
jurisdiction TEXT NULL
document_type TEXT NULL
status TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
archived_at TIMESTAMPTZ NULL
```

Recommended statuses:

`ACTIVE`, `REVIEW`, `COMPLETED`, `ARCHIVED`

### 4.4 case_members

Supports controlled collaboration.

```text
id UUID PK
case_id UUID FK cases.id
user_id UUID FK users.id
role TEXT
created_at TIMESTAMPTZ
UNIQUE(case_id, user_id)
```

Roles:

- `OWNER`
- `INVESTIGATOR`
- `REVIEWER`
- `VIEWER`

### 4.5 recordings

```text
id UUID PK
case_id UUID FK cases.id
uploaded_by UUID FK users.id
original_filename TEXT
mime_type TEXT
storage_key TEXT
sha256_hash TEXT
file_size_bytes BIGINT
duration_ms BIGINT NULL
processing_status TEXT
asr_provider TEXT NULL
asr_model TEXT NULL
created_at TIMESTAMPTZ
processed_at TIMESTAMPTZ NULL
```

The SHA-256 hash is an integrity identifier for the stored bytes. It does not prove authenticity or truthfulness.

### 4.6 transcript_segments

```text
id UUID PK
recording_id UUID FK recordings.id
sequence_number INT
speaker_label TEXT NULL
start_ms BIGINT
end_ms BIGINT
text TEXT
quality_score NUMERIC NULL
is_user_edited BOOLEAN DEFAULT FALSE
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
UNIQUE(recording_id, sequence_number)
```

### 4.7 documents

Logical document identity.

```text
id UUID PK
case_id UUID FK cases.id
uploaded_by UUID FK users.id
name TEXT
document_type TEXT NULL
jurisdiction TEXT NULL
created_at TIMESTAMPTZ
```

### 4.8 document_versions

```text
id UUID PK
document_id UUID FK documents.id
version_label TEXT
source_filename TEXT
mime_type TEXT
storage_key TEXT
sha256_hash TEXT
effective_from DATE NULL
effective_to DATE NULL
is_current BOOLEAN
page_count INT NULL
processing_status TEXT
created_at TIMESTAMPTZ
```

Never assume the latest uploaded document is legally the effective document. Version/effective-date metadata must be considered.

### 4.9 document_chunks

```text
id UUID PK
document_version_id UUID FK document_versions.id
page_number INT NULL
section_label TEXT NULL
clause_label TEXT NULL
paragraph_index INT NULL
content TEXT
content_hash TEXT
embedding VECTOR(...) NULL
search_text TSVECTOR NULL
metadata JSONB
created_at TIMESTAMPTZ
```

If pgvector is enabled, choose embedding dimension according to the selected local embedding model. Do not hardcode 384 merely because the original PRD used MiniLM.

### 4.10 findings

```text
id UUID PK
case_id UUID FK cases.id
recording_id UUID FK recordings.id NULL
statement_segment_id UUID FK transcript_segments.id NULL
document_version_id UUID FK document_versions.id NULL
status TEXT
relation_type TEXT
summary TEXT
explanation TEXT
model_name TEXT NULL
model_version TEXT NULL
prompt_version TEXT NULL
retrieval_config_version TEXT NULL
quality_metadata JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

Recommended statuses:

`AI_GENERATED`, `NEEDS_REVIEW`, `CONFIRMED`, `DISMISSED`, `SUPERSEDED`

Recommended relation types:

`CONSISTENT`, `POSSIBLE_DISCREPANCY`, `CONDITIONAL`, `TEMPORAL_OR_VERSION_MISMATCH`, `DEFINITION_OR_EXCEPTION_MISMATCH`, `INSUFFICIENT_EVIDENCE`, `NEEDS_HUMAN_REVIEW`

### 4.11 finding_evidence

This is the central provenance table.

```text
id UUID PK
finding_id UUID FK findings.id
evidence_type TEXT
recording_id UUID NULL
document_version_id UUID NULL
transcript_segment_id UUID NULL
document_chunk_id UUID NULL
quoted_text TEXT
start_ms BIGINT NULL
end_ms BIGINT NULL
page_number INT NULL
clause_label TEXT NULL
content_hash TEXT NULL
created_at TIMESTAMPTZ
```

An evidence record must identify exactly where the displayed evidence came from.

### 4.12 finding_reviews

```text
id UUID PK
finding_id UUID FK findings.id
reviewer_user_id UUID FK users.id
decision TEXT
comment TEXT NULL
reviewed_at TIMESTAMPTZ
```

Decisions:

`CONFIRM`, `DISMISS`, `NEEDS_MORE_EVIDENCE`, `CORRECT_TRANSCRIPT`, `CORRECT_SOURCE`

### 4.13 reports

```text
id UUID PK
case_id UUID FK cases.id
generated_by UUID FK users.id
report_type TEXT
storage_key TEXT
content_hash TEXT
created_at TIMESTAMPTZ
```

### 4.14 audit_logs

```text
id UUID PK
user_id UUID FK users.id NULL
case_id UUID FK cases.id NULL
action TEXT
entity_type TEXT
entity_id UUID NULL
metadata JSONB
created_at TIMESTAMPTZ
```

Audit logs should capture security-sensitive and evidence-relevant actions without storing unnecessary sensitive content.

## 5. User isolation rules

Every protected table must be reachable through an ownership or membership path.

Example authorization rule:

```text
request.user
  → case_members / cases.owner_user_id
  → requested case
  → related recording/document/finding
```

The backend must enforce this relationship on every protected operation.

If PostgreSQL Row-Level Security is used, policies must mirror the application authorization model. Database grants and application authorization must both be reviewed.

## 6. Index recommendations

At minimum evaluate indexes on:

```text
cases(owner_user_id)
case_members(user_id, case_id)
recordings(case_id)
transcript_segments(recording_id, sequence_number)
documents(case_id)
document_versions(document_id, is_current)
document_chunks(document_version_id, page_number)
findings(case_id, status)
finding_evidence(finding_id)
finding_reviews(finding_id)
audit_logs(case_id, created_at)
```

Add full-text/vector indexes according to measured query requirements.

## 7. Data retention

Retention must be configurable by deployment policy. Original evidence, derived artifacts, reports and audit logs must have explicit lifecycle rules.

Never silently delete source evidence because a case is archived.

## 8. Acceptance criteria

- A user can see only authorized cases.
- Every case has an owner.
- Every recording/document is linked to a case.
- Every finding can point to transcript and document evidence.
- Document versions are preserved.
- Human review decisions are preserved.
- Audit events identify actor, action, entity and time.
- Database constraints prevent orphaned critical records.
