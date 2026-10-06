from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import SupabaseAPIError, SupabaseUserClient, current_user_client

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _safe_db_error() -> HTTPException:
    return HTTPException(502, "Dashboard information could not be loaded.")


@router.get("/dashboard")
async def dashboard(context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client)) -> dict[str, Any]:
    """Return only data visible to the caller's Supabase JWT and database RLS."""
    client, user = context
    try:
        cases = await client.select("cases", {"select": "id,case_number,title,status,created_at,updated_at", "order": "updated_at.desc", "limit": "100"})
        findings = await client.select("findings", {"select": "id,case_id,relation_type,status,summary,created_at,updated_at", "order": "created_at.desc", "limit": "100"})
        documents = await client.select("documents", {"select": "id,case_id,name,created_at", "order": "created_at.desc", "limit": "100"})
        recordings = await client.select("recordings", {"select": "id,case_id,original_filename,processing_status,created_at", "order": "created_at.desc", "limit": "100"})
        audit = await client.select("audit_events", {"select": "id,case_id,action,entity_type,entity_id,actor_user_id,created_at", "order": "created_at.desc", "limit": "12"})
        legal_analyses = await client.select("legal_analyses", {"select": "id,case_id,status,created_at", "order": "created_at.desc", "limit": "100"})
        recommendations = await client.select("investigation_recommendations", {"select": "id,case_id,status,created_at", "order": "created_at.desc", "limit": "100"})
        profiles = await client.select("profiles", {"select": "display_name", "id": f"eq.{user['id']}", "limit": "1"})
    except SupabaseAPIError as exc:
        raise _safe_db_error() from exc

    cases_by_id = {case["id"]: case for case in cases}
    evidence_counts: dict[str, int] = {}
    for item in [*documents, *recordings]:
        evidence_counts[item["case_id"]] = evidence_counts.get(item["case_id"], 0) + 1
    finding_counts: dict[str, int] = {}
    for item in findings:
        finding_counts[item["case_id"]] = finding_counts.get(item["case_id"], 0) + 1
    recent_cases = [
        {
            **case,
            "evidence_count": evidence_counts.get(case["id"], 0),
            "finding_count": finding_counts.get(case["id"], 0),
            "document_status": "UPLOADED" if any(item["case_id"] == case["id"] for item in documents) else "REQUIRED",
            "audio_status": next((item.get("processing_status", "UPLOADED") for item in recordings if item["case_id"] == case["id"]), "NOT PROVIDED"),
            "finding_status": next((item.get("relation_type", "RECORDED") for item in findings if item["case_id"] == case["id"]), "PENDING"),
            "review_status": next((item.get("status", "NEEDS REVIEW") for item in findings if item["case_id"] == case["id"]), "PENDING"),
        }
        for case in cases[:8]
    ]
    review_count = sum(1 for finding in findings if finding.get("status") in {"NEEDS_REVIEW", "NEEDS_MORE_REVIEW"})
    discrepancy_count = sum(1 for finding in findings if finding.get("relation_type") == "POSSIBLE_DISCREPANCY")
    verified_count = sum(1 for finding in findings if finding.get("status") == "VERIFIED")
    insufficient_count = sum(1 for finding in findings if finding.get("relation_type") == "INSUFFICIENT_EVIDENCE")
    return {
        "profile": {"display_name": profiles[0].get("display_name", "") if profiles else "", "email": user.get("email")},
        "stats": {"active_cases": sum(1 for case in cases if case.get("status") in {"ACTIVE", "REVIEW"}), "awaiting_review": review_count, "possible_discrepancies": discrepancy_count, "insufficient_evidence": insufficient_count, "human_verified": verified_count, "evidence_items": len(documents) + len(recordings), "pending_actions": review_count, "legal_intelligence_items": sum(1 for item in legal_analyses if item.get("status") == "COMPLETED"), "recommendations": sum(1 for item in recommendations if item.get("status") == "OPEN")},
        "cases": recent_cases,
        "findings": [{**finding, "case_title": cases_by_id.get(finding["case_id"], {}).get("title", "Case")} for finding in findings[:8]],
        "activity": [{**item, "case_title": cases_by_id.get(item["case_id"], {}).get("title", "Case")} for item in audit],
        "data_scope": {"limit_per_record_type": 100, "cases": len(cases), "findings": len(findings), "documents": len(documents), "recordings": len(recordings)},
    }
