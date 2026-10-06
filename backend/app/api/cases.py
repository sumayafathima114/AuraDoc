from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.core.authorization import require_case_role
from app.core.config import settings
from app.core.supabase import SupabaseAPIError, SupabaseUserClient, current_user_client
from app.schemas.analysis import EvidenceCandidate, RelationType
from app.schemas.cases import CaseCreate, CompareRequest, DocumentMetadata, DocumentReviewRequest, RecordingMetadata, ReviewRequest
from app.services.asr import VoskASRProvider
from app.services.documents import read_and_parse_pdf
from app.services.quick_checks import describe_payment_term_conflict, find_payment_term_conflict
from app.services.retrieval import rank_sections

router = APIRouter(prefix="/api/v1", tags=["cases"])
UserContext = tuple[SupabaseUserClient, dict[str, Any]]


def _database_error(exc: SupabaseAPIError) -> HTTPException:
    if exc.error_code in {"PGRST202", "PGRST204", "PGRST205"}:
        return HTTPException(
            503,
            "The AuraDoc database schema is not available in Supabase. Apply all current AuraDoc migrations, then restart FastAPI.",
        )
    if exc.status_code in (401, 403, 404):
        return HTTPException(404, "The requested resource is unavailable.")
    if exc.status_code in (409, 422):
        return HTTPException(422, "The request conflicts with the current case data.")
    return HTTPException(502, "The data service could not complete the request.")


async def _require_case(client: SupabaseUserClient, case_id: UUID) -> dict[str, Any]:
    rows = await client.select(
        "cases",
        {"select": "id,case_number,title,description,status,created_at,updated_at", "id": f"eq.{case_id}", "limit": "1"},
    )
    if not rows:
        raise HTTPException(404, "Case not found.")
    return rows[0]


@router.get("/me")
async def me(context: UserContext = Depends(current_user_client)) -> dict[str, str | None]:
    _, user = context
    return {"id": str(user["id"]), "email": user.get("email")}


@router.get("/cases")
async def list_cases(context: UserContext = Depends(current_user_client)) -> list[dict[str, Any]]:
    client, _ = context
    try:
        return await client.select(
            "cases",
            {"select": "id,case_number,title,description,status,created_at,updated_at", "order": "created_at.desc", "limit": "100"},
        )
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc


@router.post("/cases", status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate, context: UserContext = Depends(current_user_client)
) -> dict[str, Any]:
    client, _ = context
    case_id = uuid4()
    try:
        # The membership-based SELECT policy cannot see a new row until its
        # AFTER INSERT membership trigger runs. Insert without RETURNING, then
        # fetch after PostgREST commits the trigger effects.
        await client.insert(
            "cases",
            {"id": str(case_id), **payload.model_dump()},
            return_representation=False,
        )
        return await _require_case(client, case_id)
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc


@router.get("/cases/{case_id}")
async def get_case(
    case_id: UUID, context: UserContext = Depends(current_user_client)
) -> dict[str, Any]:
    client, _ = context
    try:
        return await _require_case(client, case_id)
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc


@router.get("/cases/{case_id}/workspace")
async def get_workspace(
    case_id: UUID, context: UserContext = Depends(current_user_client)
) -> dict[str, Any]:
    client, _ = context
    try:
        case = await _require_case(client, case_id)
        documents = await client.select(
            "documents", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc"}
        )
        recordings = await client.select(
            "recordings", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc"}
        )
        findings = await client.select(
            "findings", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc"}
        )
        versions: list[dict[str, Any]] = []
        for document in documents:
            versions.extend(await client.select(
                "document_versions", {"select": "*", "document_id": f"eq.{document['id']}", "order": "created_at.desc"}
            ))
        document_sections: list[dict[str, Any]] = []
        for version in versions:
            document_sections.extend(await client.select(
                "document_sections", {"select": "id,document_version_id,page_number,section_label,clause_label,content,content_hash,paragraph_index", "document_version_id": f"eq.{version['id']}", "order": "page_number.asc,paragraph_index.asc", "limit": "1000"}
            ))
        segments: list[dict[str, Any]] = []
        for recording in recordings:
            segments.extend(await client.select(
                "transcript_segments", {"select": "*", "recording_id": f"eq.{recording['id']}", "order": "sequence_number.asc"}
            ))
        evidence: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []
        for finding in findings:
            evidence.extend(await client.select(
                "finding_evidence", {"select": "*", "finding_id": f"eq.{finding['id']}"}
            ))
            reviews.extend(await client.select(
                "review_actions", {"select": "*", "finding_id": f"eq.{finding['id']}", "order": "reviewed_at.desc", "limit": "100"}
            ))
        audit = await client.select(
            "audit_events", {"select": "id,action,entity_type,entity_id,metadata,created_at,actor_user_id", "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100"}
        )
        legal_sources = await client.select(
            "legal_sources", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100"}
        )
        legal_analyses = await client.select(
            "legal_analyses", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100"}
        )
        analysis_ids = [row["id"] for row in legal_analyses]
        legal_analysis_sources = await client.select(
            "legal_analysis_sources", {"select": "*", "legal_analysis_id": f"in.({','.join(analysis_ids)})", "limit": "1000"}
        ) if analysis_ids else []
        recommendations = await client.select(
            "investigation_recommendations", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100"}
        )
        conclusions = await client.select(
            "case_conclusions", {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc", "limit": "100"}
        )
        return {"case": case, "documents": documents, "document_versions": versions, "document_sections": document_sections,
                "recordings": recordings, "transcript_segments": segments,
                "findings": findings, "finding_evidence": evidence, "audit_events": audit,
                "legal_sources": legal_sources, "legal_analyses": legal_analyses,
                "legal_analysis_sources": legal_analysis_sources,
                "recommendations": recommendations, "review_actions": reviews,
                "case_conclusions": conclusions}
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc


@router.post("/cases/{case_id}/documents", response_model=DocumentMetadata, status_code=201)
async def upload_document(
    case_id: UUID,
    file: UploadFile = File(...),
    context: UserContext = Depends(current_user_client),
) -> DocumentMetadata:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    await _require_case(client, case_id)
    parsed = await read_and_parse_pdf(file, settings.max_upload_bytes)
    document_id, version_id = uuid4(), uuid4()
    storage_key = f"{case_id}/{document_id}/{version_id}/{parsed.sha256_hash}.pdf"
    try:
        await client.upload(storage_key, parsed.data, "application/pdf")
        result = await client.rpc(
            "register_document_ingest",
            {"p_case_id": str(case_id), "p_name": Path(parsed.filename).stem,
             "p_source_filename": parsed.filename, "p_storage_key": storage_key,
             "p_sha256_hash": parsed.sha256_hash, "p_page_count": parsed.page_count,
             "p_sections": parsed.sections},
        )
    except SupabaseAPIError as exc:
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise _database_error(exc) from exc
    except HTTPException:
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise
    if not isinstance(result, dict) or not result.get("document_id"):
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise HTTPException(502, "Document metadata could not be registered.")
    return DocumentMetadata(
        document_id=result["document_id"], version_id=result["version_id"],
        name=Path(parsed.filename).stem, version_label="v1", sha256_hash=parsed.sha256_hash,
        page_count=parsed.page_count, section_count=int(result.get("section_count", 0)),
    )


@router.post("/cases/{case_id}/recordings", response_model=RecordingMetadata, status_code=201)
async def upload_recording(
    case_id: UUID,
    file: UploadFile = File(...),
    context: UserContext = Depends(current_user_client),
) -> RecordingMetadata:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    await _require_case(client, case_id)
    filename = (file.filename or "recording.wav").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".wav") or file.content_type not in ("audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"):
        raise HTTPException(415, "The MVP ASR provider accepts WAV recordings only.")
    audio = await file.read(settings.max_upload_bytes + 1)
    if len(audio) > settings.max_upload_bytes:
        raise HTTPException(413, "The uploaded recording exceeds the configured size limit.")
    asr = VoskASRProvider()
    segments, duration_ms, model_name = await asyncio.to_thread(asr.transcribe, audio)
    digest = hashlib.sha256(audio).hexdigest()
    recording_id = uuid4()
    storage_key = f"{case_id}/{recording_id}/{digest}.wav"
    serialized_segments = [segment.__dict__ for segment in segments]
    try:
        await client.upload(storage_key, audio, "audio/wav")
        result = await client.rpc(
            "register_audio_ingest",
            {"p_case_id": str(case_id), "p_original_filename": filename,
             "p_storage_key": storage_key, "p_sha256_hash": digest,
             "p_file_size_bytes": len(audio), "p_duration_ms": duration_ms,
             "p_asr_provider": asr.provider_name, "p_asr_model": model_name,
             "p_segments": serialized_segments},
        )
    except SupabaseAPIError as exc:
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise _database_error(exc) from exc
    except HTTPException:
        # Supabase timeouts/network errors are surfaced as HTTPException by
        # the client. Remove the uploaded object if the registration RPC fails.
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise
    if not isinstance(result, dict) or not result.get("recording_id"):
        try:
            await client.remove_object(storage_key)
        except Exception:
            pass
        raise HTTPException(502, "Recording metadata could not be registered.")
    return RecordingMetadata(
        recording_id=result["recording_id"], sha256_hash=digest,
        duration_ms=duration_ms, segment_count=int(result.get("segment_count", 0)),
        asr_provider=asr.provider_name, asr_model=model_name,
    )


@router.post("/cases/{case_id}/compare")
async def compare_statement(
    request: Request, case_id: UUID, payload: CompareRequest,
    context: UserContext = Depends(current_user_client),
) -> dict[str, Any]:
    from app.ai.nvidia import NVIDIAProvider, ProviderInvalidResponse, ProviderUnavailable

    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    await _require_case(client, case_id)
    try:
        segments = await client.select(
            "transcript_segments", {"select": "*", "id": f"eq.{payload.transcript_segment_id}", "limit": "1"}
        )
        if not segments:
            raise HTTPException(404, "Transcript segment not found.")
        segment = segments[0]
        recordings = await client.select(
            "recordings", {"select": "id,case_id", "id": f"eq.{segment['recording_id']}", "case_id": f"eq.{case_id}", "limit": "1"}
        )
        if not recordings:
            raise HTTPException(404, "Transcript segment not found.")
        version = await client.select(
            "document_versions", {"select": "id,document_id,version_label", "id": f"eq.{payload.document_version_id}", "limit": "1"}
        )
        if not version:
            raise HTTPException(404, "Document version not found.")
        docs = await client.select(
            "documents", {"select": "id,case_id,name", "id": f"eq.{version[0]['document_id']}", "case_id": f"eq.{case_id}", "limit": "1"}
        )
        if not docs:
            raise HTTPException(404, "Document version not found.")
        sections = await client.select(
            "document_sections", {"select": "id,page_number,section_label,clause_label,content,content_hash", "document_version_id": f"eq.{payload.document_version_id}", "limit": "1000"}
        )
        ranked = rank_sections(segment["text"], sections, limit=5)
        candidates = [EvidenceCandidate(
            section_id=row["id"], document_name=docs[0]["name"],
            version_label=version[0]["version_label"], page_number=row["page_number"],
            section_label=row.get("section_label"), clause_label=row.get("clause_label"),
            content=row["content"], content_hash=row["content_hash"],
        ) for row in ranked]
        if not candidates:
            candidates = []
        provider = NVIDIAProvider(http_client=getattr(request.app.state, "nvidia_http_client", None))
        assessment = await provider.compare(segment["text"], candidates)
        by_id = {row["id"]: row for row in ranked}
        evidence = [{
            "document_section_id": row["id"], "quoted_text": row["content"],
            "page_number": row["page_number"], "section_label": row.get("section_label"),
            "clause_label": row.get("clause_label"), "source_hash": row["content_hash"],
        } for row in (by_id[section_id] for section_id in assessment.supporting_section_ids)]
        evidence.append({
            "transcript_segment_id": str(payload.transcript_segment_id),
            "quoted_text": segment["text"], "start_ms": segment["start_ms"],
            "end_ms": segment["end_ms"],
            "source_hash": segment["source_hash"],
        })
        saved = await client.rpc(
            "register_finding",
            {"p_case_id": str(case_id), "p_recording_id": str(segment["recording_id"]),
             "p_transcript_segment_id": str(payload.transcript_segment_id),
             "p_document_version_id": str(payload.document_version_id),
             "p_relation_type": assessment.relation.value, "p_summary": assessment.summary,
             "p_explanation": assessment.explanation,
             "p_uncertainties": assessment.uncertainties,
             "p_provider": provider.provider_name, "p_model_name": provider.model_name,
             "p_prompt_version": "auradoc-comparison-v1", "p_evidence": evidence},
        )
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ProviderInvalidResponse as exc:
        raise HTTPException(502, str(exc)) from exc
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc
    return {**saved, "assessment": assessment.model_dump(mode="json"),
            "provider": provider.provider_name, "model_name": provider.model_name,
            "ai_status": "AI_READY", "human_review_required": True}


@router.post("/cases/{case_id}/documents/{document_version_id}/review", status_code=201)
async def review_document_only(
    request: Request, case_id: UUID, document_version_id: UUID, payload: DocumentReviewRequest,
    context: UserContext = Depends(current_user_client),
) -> dict[str, Any]:
    """Review extracted document evidence without implying audio or a comparison."""
    from app.ai.nvidia import NVIDIAProvider, ProviderInvalidResponse, ProviderUnavailable

    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    await _require_case(client, case_id)
    try:
        versions = await client.select("document_versions", {
            "select": "id,document_id,version_label,page_count,sha256_hash",
            "id": f"eq.{document_version_id}", "limit": "1",
        })
        if not versions:
            raise HTTPException(404, "Document version not found.")
        version = versions[0]
        docs = await client.select("documents", {
            "select": "id,case_id,name", "id": f"eq.{version['document_id']}",
            "case_id": f"eq.{case_id}", "limit": "1",
        })
        if not docs:
            raise HTTPException(404, "Document version not found.")
        sections = await client.select("document_sections", {
            "select": "id,page_number,section_label,clause_label,content,content_hash",
            "document_version_id": f"eq.{document_version_id}", "order": "page_number.asc,paragraph_index.asc", "limit": "1000",
        })
        if not sections:
            raise HTTPException(422, "This document has no extracted text available for review.")
        focus = (payload.focus_question or "payment obligations dates terms conditions exceptions definitions amendments").strip()
        ranked = rank_sections(focus, sections, limit=8) or sections[:8]
        candidates = [EvidenceCandidate(
            section_id=row["id"], document_name=docs[0]["name"],
            version_label=version["version_label"], page_number=row["page_number"],
            section_label=row.get("section_label"), clause_label=row.get("clause_label"),
            content=row["content"], content_hash=row["content_hash"],
        ) for row in ranked]
    except HTTPException:
        raise
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc

    provider = NVIDIAProvider(http_client=getattr(request.app.state, "nvidia_http_client", None))
    try:
        assessment = await provider.review_document(candidates, payload.focus_question)
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ProviderInvalidResponse as exc:
        raise HTTPException(502, str(exc)) from exc

    by_id = {row["id"]: row for row in ranked}
    evidence = [{
        "document_section_id": section_id, "quoted_text": by_id[section_id]["content"],
        "page_number": by_id[section_id]["page_number"],
        "section_label": by_id[section_id].get("section_label"),
        "clause_label": by_id[section_id].get("clause_label"),
        "source_hash": by_id[section_id]["content_hash"],
    } for section_id in assessment.supporting_section_ids]
    try:
        saved = await client.rpc("register_document_finding", {
            "p_case_id": str(case_id), "p_document_version_id": str(document_version_id),
            "p_summary": assessment.summary, "p_explanation": assessment.explanation,
            "p_uncertainties": assessment.uncertainties, "p_provider": provider.provider_name,
            "p_model_name": provider.model_name, "p_prompt_version": "auradoc-document-review-v1",
            "p_evidence": evidence,
        })
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc
    if not isinstance(saved, dict) or not saved.get("finding_id"):
        raise HTTPException(502, "Document review could not be persisted.")
    return {**saved, "analysis_mode": "DOCUMENT_REVIEW",
            "relation": RelationType.NEEDS_HUMAN_REVIEW.value,
            "assessment": assessment.model_dump(mode="json"), "provider": provider.provider_name,
            "model_name": provider.model_name, "ai_status": "AI_READY", "human_review_required": True,
            "message": "Document-only review created. No transcript comparison was performed."}


@router.post("/cases/{case_id}/documents/{document_version_id}/quick-check", status_code=200)
async def quick_check_document(
    case_id: UUID, document_version_id: UUID,
    context: UserContext = Depends(current_user_client),
) -> dict[str, Any]:
    """Run a narrow local payment-deadline check, explicitly distinct from AI."""
    started_at = time.perf_counter()
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "INVESTIGATOR"})
    await _require_case(client, case_id)
    try:
        versions = await client.select(
            "document_versions",
            {"select": "id,document_id", "id": f"eq.{document_version_id}", "limit": "1"},
        )
        if not versions:
            raise HTTPException(404, "Document version not found.")
        documents = await client.select(
            "documents",
            {"select": "id", "id": f"eq.{versions[0]['document_id']}", "case_id": f"eq.{case_id}", "limit": "1"},
        )
        if not documents:
            raise HTTPException(404, "Document version not found.")
        sections = await client.select(
            "document_sections",
            {"select": "id,page_number,section_label,clause_label,content,content_hash",
             "document_version_id": f"eq.{document_version_id}", "limit": "1000"},
        )
        conflict = find_payment_term_conflict(sections)
        if conflict is None:
            return {
                "status": "NO_AUTOMATED_CONFLICT_DETECTED",
                "analysis_type": "DETERMINISTIC_CHECK_NOT_AI",
                "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "message": "The fast payment-deadline check found no directly comparable conflicting values. This does not establish that the document is complete or legally valid.",
                "finding_id": None,
                "human_review_required": True,
            }
        summary, explanation, uncertainties = describe_payment_term_conflict(conflict)
        section_ids = list(dict.fromkeys(term.section_id for term in conflict.terms if term.section_id))
        evidence_rows = {row["id"]: row for row in sections if row.get("id") in section_ids}
        if not evidence_rows or set(evidence_rows) != set(section_ids):
            raise HTTPException(422, "The deterministic check could not preserve its source evidence.")
        evidence = [{
            "document_section_id": row["id"], "quoted_text": row["content"],
            "page_number": row["page_number"], "section_label": row.get("section_label"),
            "clause_label": row.get("clause_label"), "source_hash": row["content_hash"],
        } for row in evidence_rows.values()]
        saved = await client.rpc("register_document_finding", {
            "p_case_id": str(case_id), "p_document_version_id": str(document_version_id),
            "p_summary": summary, "p_explanation": explanation,
            "p_uncertainties": uncertainties, "p_provider": "auradoc-deterministic",
            "p_model_name": "payment-deadline-check-v1",
            "p_prompt_version": "deterministic-payment-deadline-v1", "p_evidence": evidence,
        })
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc
    if not isinstance(saved, dict) or not saved.get("finding_id"):
        raise HTTPException(502, "The deterministic finding could not be persisted.")
    return {
        **saved, "status": "DETERMINISTIC_CHECK_REQUIRES_HUMAN_REVIEW",
        "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
        "analysis_type": "DETERMINISTIC_CHECK_NOT_AI",
        "relation": RelationType.NEEDS_HUMAN_REVIEW.value,
        "summary": summary, "explanation": explanation, "uncertainties": uncertainties,
        "provider": "auradoc-deterministic", "model_name": "payment-deadline-check-v1",
        "human_review_required": True,
    }


@router.post("/cases/{case_id}/findings/{finding_id}/review", status_code=201)
async def review_finding(
    case_id: UUID, finding_id: UUID, payload: ReviewRequest,
    context: UserContext = Depends(current_user_client),
) -> dict[str, Any]:
    client, user = context
    await require_case_role(client, case_id, user["id"], {"OWNER", "REVIEWER"})
    await _require_case(client, case_id)
    try:
        findings = await client.select(
            "findings", {"select": "id", "id": f"eq.{finding_id}", "case_id": f"eq.{case_id}", "limit": "1"}
        )
        if not findings:
            raise HTTPException(404, "Finding not found.")
        rows = await client.insert(
            "review_actions",
            {"finding_id": str(finding_id), "reviewer_user_id": str(user["id"]),
             "decision": payload.decision.value, "comment": payload.comment},
        )
    except SupabaseAPIError as exc:
        raise _database_error(exc) from exc
    if not rows:
        raise HTTPException(502, "The review action could not be recorded.")
    return rows[0]
