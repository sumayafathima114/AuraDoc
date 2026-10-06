# Legal Intelligence status

## Implemented

- The authenticated `/legal-intelligence` page links to India Code and the Supreme Court portals. These are **external portal references**, not AuraDoc-retrieved legal records.
- Case-scoped legal-source records, review statuses, human attestation, legal analyses, recommendations, and audit triggers are represented in the existing database migration and API.
- Source intake is user-supplied and restricted to configured official HTTPS hostnames. Pending sources are not automatically treated as verified.
- Legal analysis selects only records with the `VERIFIED_OFFICIAL` status and constrains cited source IDs to supplied records. With no verified source it returns `NO_VERIFIED_LEGAL_SOURCE_FOUND` rather than asking the model to supply law from memory.

## Important meaning of verification

`VERIFIED_OFFICIAL` reflects the recorded human review/attestation workflow. It does not mean AuraDoc cryptographically authenticated the content, independently confirmed legal validity, or proved current applicability. Reviewers must verify the source and version for the relevant case date. The NVIDIA model is an analysis layer and cannot establish legal authority.

## Not implemented / not verified

- Automated India Code or Supreme Court ingestion and refresh.
- Independent source/citation verification by AuraDoc.
- A successful live NVIDIA legal relevance request on a persisted finding.
- End-to-end missing-evidence/recommendation persistence and human review on a live case.
- A safe lifecycle for retiring a previously attested source as outdated requires a database migration and target-project validation.

If no verified source is available, the application must state that the source could not be verified and avoid legal conclusions. Current portal references:

- India Code: <https://www.indiacode.nic.in/>
- Supreme Court of India: <https://www.sci.gov.in/>
- Supreme Court judgment search portal: <https://scr.sci.gov.in/scrsearch/>
