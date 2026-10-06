from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai.nvidia import NVIDIAProvider, ProviderInvalidResponse, ProviderUnavailable
from app.core.authorization import require_case_role
from app.core.supabase import SupabaseAPIError, SupabaseUserClient, current_user_client
from app.schemas.analysis import LegalSourceEvidence
from app.schemas.cases import HumanConclusionRequest, LegalSourceCreate, LegalSourceReview, RecommendationStatusUpdate
from app.services.retrieval import rank_sections

router = APIRouter(prefix="/api/v1", tags=["legal intelligence"])
PROMPT_VERSION = "auradoc-legal-relevance-v1"
SOURCE_COLUMNS = "id,case_id,title,source_type,jurisdiction,authority,act_or_regulation,section,subsection,publication_date,effective_date,version_label,official_source_url,retrieved_at,verification_status,source_text,source_sha256,verified_by,verified_at,verification_notes,created_at,updated_at"


def _allowed_official_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme == "https" and parsed.port in (None, 443) and (
            host == "indiacode.nic.in" or host.endswith(".indiacode.nic.in")
            or host == "sci.gov.in" or host.endswith(".sci.gov.in")
        ) and not parsed.username and not parsed.password
    except ValueError:
        return False


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.get("/legal-sources")
async def list_accessible_legal_sources(
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> list[dict[str, Any]]:
    client, _ = context
    try:
        rows = await client.select("legal_sources", {
            "select": "id,case_id,title,source_type,jurisdiction,authority,act_or_regulation,section,subsection,publication_date,effective_date,version_label,official_source_url,retrieved_at,verification_status,source_sha256,verified_at,verification_notes,created_at",
            "order": "created_at.desc", "limit": "200",
        })
        cases = await client.select("cases", {"select": "id,title", "limit": "100"})
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    title_by_case = {case["id"]: case["title"] for case in cases}
    return [{**row, "case_title": title_by_case.get(row["case_id"], "Case")} for row in rows]


def _db_failure(exc: SupabaseAPIError) -> HTTPException:
    if exc.error_code in {"PGRST202", "PGRST204", "PGRST205"}:
        return HTTPException(503, "The legal workflow migration is not available. Apply the latest AuraDoc migration.")
    if exc.status_code in (401, 403, 404):
        return HTTPException(404, "The requested case resource is unavailable.")
    return HTTPException(502, "The legal workflow could not be completed.")


@router.get("/cases/{case_id}/legal-sources")
async def list_legal_sources(
    case_id: UUID, context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> list[dict[str, Any]]:
    client, _ = context
    try:
        return await client.select("legal_sources", {
            "select": SOURCE_COLUMNS, "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100",
        })
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc


@router.post("/cases/{case_id}/legal-sources", status_code=status.HTTP_201_CREATED)
async def ingest_legal_source(
    case_id: UUID,
    payload: LegalSourceCreate,
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> dict[str, Any]:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    if not _allowed_official_url(payload.official_source_url):
        raise HTTPException(422, "Use an HTTPS India Code or Supreme Court of India source URL.")
    normalized = payload.model_dump(mode="json")
    normalized["official_source_url"] = payload.official_source_url.strip()
    normalized["source_sha256"] = _source_hash(payload.source_text)
    normalized["created_by"] = str(user["id"])
    try:
        rows = await client.insert("legal_sources", {"case_id": str(case_id), **normalized})
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    if not rows:
        raise HTTPException(502, "The legal source could not be recorded.")
    return rows[0]


@router.post("/cases/{case_id}/legal-sources/{source_id}/review")
async def review_legal_source(
    case_id: UUID,
    source_id: UUID,
    payload: LegalSourceReview,
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> dict[str, Any]:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "REVIEWER"})
    try:
        sources = await client.select("legal_sources", {
            "select": "id,verification_status", "id": f"eq.{source_id}", "case_id": f"eq.{case_id}", "limit": "1",
        })
        if not sources:
            raise HTTPException(404, "Legal source not found.")
        if sources[0]["verification_status"] != "PENDING_VERIFICATION":
            raise HTTPException(409, "This legal-source record has already been reviewed. Ingest a new version to change it.")
        is_verified = payload.verification_status == "VERIFIED_OFFICIAL"
        rows = await client.request(
            "PATCH", "/rest/v1/legal_sources",
            params={"id": f"eq.{source_id}", "case_id": f"eq.{case_id}", "select": SOURCE_COLUMNS},
            json={
                "verification_status": payload.verification_status,
                "verified_by": str(user["id"]) if is_verified else None,
                "verified_at": datetime.now(timezone.utc).isoformat() if is_verified else None,
                "verification_notes": payload.verification_notes,
            },
            headers={"Prefer": "return=representation"},
        )
    except HTTPException:
        raise
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    if not isinstance(rows, list) or not rows:
        raise HTTPException(403, "Only a case owner or reviewer can review legal sources.")
    return rows[0]


@router.post("/cases/{case_id}/findings/{finding_id}/legal-analysis", status_code=status.HTTP_201_CREATED)
async def analyze_finding_legal_context(
    request: Request,
    case_id: UUID,
    finding_id: UUID,
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> dict[str, Any]:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    try:
        findings = await client.select("findings", {
            "select": "id,case_id,relation_type,status,summary,explanation,uncertainties,created_at",
            "id": f"eq.{finding_id}", "case_id": f"eq.{case_id}", "limit": "1",
        })
        if not findings:
            raise HTTPException(404, "Finding not found.")
        finding = findings[0]
        references = await client.select("finding_evidence", {
            "select": "quoted_text,start_ms,end_ms,page_number,section_label,clause_label,document_section_id,transcript_segment_id,source_hash",
            "finding_id": f"eq.{finding_id}", "limit": "30",
        })
        source_rows = await client.select("legal_sources", {
            "select": SOURCE_COLUMNS, "case_id": f"eq.{case_id}",
            "verification_status": "eq.VERIFIED_OFFICIAL", "order": "verified_at.desc", "limit": "100",
        })
    except HTTPException:
        raise
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc

    query = f"{finding['summary']} {finding['explanation']}"
    ranked = rank_sections(query, [
        {"id": source["id"], "content": f"{source['title']} {source.get('act_or_regulation') or ''} {source.get('section') or ''} {source['source_text']}", "page_number": 1}
        for source in source_rows
    ], limit=8)
    sources_by_id = {source["id"]: source for source in source_rows}
    selected_sources = [sources_by_id[row["id"]] for row in ranked]
    # Cap request size while preserving source provenance; originals remain unchanged in PostgreSQL.
    model_sources = [LegalSourceEvidence.model_validate({
        key: source.get(key) for key in LegalSourceEvidence.model_fields
    } | {"source_text": source["source_text"][:16000]}) for source in selected_sources]
    provider = NVIDIAProvider(http_client=request.app.state.nvidia_http_client)
    try:
        assessment = await provider.analyze_legal_relevance(finding, model_sources, references)
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ProviderInvalidResponse as exc:
        raise HTTPException(502, str(exc)) from exc

    no_source = not model_sources
    referenced_ids = {str(item.legal_source_id) for item in assessment.legal_relevance}
    referenced_ids.update(str(item.legal_source_id) for item in assessment.recommendations if item.legal_source_id)
    source_ids = sorted(referenced_ids)
    try:
        saved = await client.rpc("register_legal_analysis", {
            "p_case_id": str(case_id), "p_finding_id": str(finding_id),
            "p_status": "NO_VERIFIED_LEGAL_SOURCE_FOUND" if no_source else "COMPLETED",
            "p_legal_relevance": [item.model_dump(mode="json") for item in assessment.legal_relevance],
            "p_missing_evidence": assessment.missing_evidence,
            "p_provider": provider.provider_name, "p_model_name": provider.model_name,
            "p_prompt_version": "auradoc-legal-relevance-v1", "p_source_ids": source_ids,
            "p_recommendations": [item.model_dump(mode="json") for item in assessment.recommendations],
        })
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    if not isinstance(saved, dict) or not saved.get("legal_analysis_id"):
        raise HTTPException(502, "Legal analysis could not be persisted.")
    return {
        "legal_analysis_id": saved["legal_analysis_id"], "finding_id": str(finding_id),
        "status": "NO_VERIFIED_LEGAL_SOURCE_FOUND" if no_source else "COMPLETED",
        "legal_relevance": [item.model_dump(mode="json") for item in assessment.legal_relevance],
        "legal_sources": selected_sources, "missing_evidence": assessment.missing_evidence,
        "recommendations": assessment.recommendations,
        "provider": provider.provider_name, "model_name": provider.model_name, "ai_status": "AI_READY",
        "requires_human_review": True,
        "message": "Unable to verify this legal source." if no_source else "Legal relevance is an AI analysis of source records reviewed by a human; independently verify applicability.",
    }


@router.post("/cases/{case_id}/findings/{finding_id}/conclusions", status_code=status.HTTP_201_CREATED)
async def create_human_conclusion(
    case_id: UUID,
    finding_id: UUID,
    payload: HumanConclusionRequest,
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> dict[str, Any]:
    """Persist a reviewer-authored conclusion and snapshots of its case evidence."""
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "REVIEWER"})
    try:
        findings = await client.select("findings", {
            "select": "id", "id": f"eq.{finding_id}", "case_id": f"eq.{case_id}", "limit": "1",
        })
        if not findings:
            raise HTTPException(404, "Finding not found.")
        saved = await client.rpc("register_human_conclusion", {
            "p_case_id": str(case_id), "p_finding_id": str(finding_id),
            "p_lawyer_recommendation": payload.lawyer_recommendation,
            "p_human_conclusion": payload.human_conclusion,
            "p_limitations": payload.limitations,
        })
    except HTTPException:
        raise
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    if not isinstance(saved, dict) or not saved.get("conclusion_id"):
        raise HTTPException(502, "Human conclusion could not be persisted.")
    return {
        "conclusion_id": saved["conclusion_id"], "case_id": str(case_id),
        "finding_id": str(finding_id), "reviewer_user_id": str(user["id"]),
        "status": "HUMAN_CONCLUSION_CREATED", "ai_generated": False,
    }


@router.patch("/cases/{case_id}/recommendations/{recommendation_id}")
async def update_recommendation(
    case_id: UUID,
    recommendation_id: UUID,
    payload: RecommendationStatusUpdate,
    context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client),
) -> dict[str, Any]:
    next_status = payload.status
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "REVIEWER"})
    try:
        rows = await client.request(
            "PATCH", "/rest/v1/investigation_recommendations",
            params={"id": f"eq.{recommendation_id}", "case_id": f"eq.{case_id}", "select": "id,case_id,finding_id,action,reason,evidence_basis,priority,status,updated_at"},
            json={"status": next_status, "updated_at": datetime.now(timezone.utc).isoformat()},
            headers={"Prefer": "return=representation"},
        )
    except SupabaseAPIError as exc:
        raise _db_failure(exc) from exc
    if not isinstance(rows, list) or not rows:
        raise HTTPException(403, "Only a case owner or reviewer can update recommendations.")
    return rows[0]
