from app.services.quick_checks import describe_payment_term_conflict, find_payment_term_conflict


def test_detects_different_payment_deadlines_and_preserves_source_sections() -> None:
    conflict = find_payment_term_conflict([
        {"id": "section-a", "page_number": 1, "content": "Payment shall be completed within 60 days of invoice receipt."},
        {"id": "section-b", "page_number": 2, "content": "Payment must be made within 30 days of receiving an invoice."},
    ])

    assert conflict is not None
    assert {term.section_id for term in conflict.terms} == {"section-a", "section-b"}
    summary, explanation, uncertainties = describe_payment_term_conflict(conflict)
    assert "30 days" in summary and "60 days" in summary
    assert "cannot determine" in explanation
    assert "NOT AI ANALYSIS" in uncertainties[0]


def test_does_not_flag_one_payment_deadline() -> None:
    assert find_payment_term_conflict([
        {"id": "section-a", "page_number": 1, "content": "Payment shall be completed within 60 days of invoice receipt."},
    ]) is None


def test_does_not_pair_unrelated_duration_with_payment_term() -> None:
    assert find_payment_term_conflict([
        {"id": "section-a", "page_number": 1, "content": "Payment shall be completed within 60 days."},
        {"id": "section-b", "page_number": 2, "content": "The service warranty lasts for 30 days."},
    ]) is None


def test_mock_api_persists_deterministic_result_with_the_supplied_source(monkeypatch) -> None:
    """TEST MOCK — verifies route wiring and provenance, not live database RLS."""
    from fastapi.testclient import TestClient

    from app.core.supabase import current_user_client
    from app.main import app

    case_id = "00000000-0000-0000-0000-000000000031"
    version_id = "00000000-0000-0000-0000-000000000032"
    section_a = "00000000-0000-0000-0000-000000000033"
    section_b = "00000000-0000-0000-0000-000000000034"
    stored: dict = {}

    class MockClient:
        async def select(self, table, params):
            if table == "case_members": return [{"role": "OWNER"}]
            if table == "cases": return [{"id": case_id, "case_number": "AD-TEST", "title": "Fictional test", "description": "", "status": "ACTIVE", "created_at": "2026-10-06", "updated_at": "2026-10-06"}]
            if table == "document_versions": return [{"id": version_id, "document_id": "document-1"}]
            if table == "documents": return [{"id": "document-1", "case_id": case_id}]
            if table == "document_sections": return [
                {"id": section_a, "page_number": 1, "section_label": "Payment Terms", "clause_label": "7.1", "content": "Payment shall be completed within 60 days of invoice receipt.", "content_hash": "a" * 64},
                {"id": section_b, "page_number": 2, "section_label": "Payment Terms", "clause_label": "8.2", "content": "Payment must be made within 30 days of receiving an invoice.", "content_hash": "b" * 64},
            ]
            return []

        async def rpc(self, name, payload):
            assert name == "register_document_finding"
            stored.update(payload)
            return {"finding_id": "00000000-0000-0000-0000-000000000035", "evidence_count": len(payload["p_evidence"])}

    async def context():
        yield MockClient(), {"id": "00000000-0000-0000-0000-000000000036", "email": "investigator@example.test"}

    app.dependency_overrides[current_user_client] = context
    try:
        response = TestClient(app).post(f"/api/v1/cases/{case_id}/documents/{version_id}/quick-check")
    finally:
        app.dependency_overrides.pop(current_user_client, None)

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_type"] == "DETERMINISTIC_CHECK_NOT_AI"
    assert isinstance(body["elapsed_ms"], (int, float)) and body["elapsed_ms"] >= 0
    assert body["human_review_required"] is True
    assert body["evidence_count"] == 2
    assert stored["p_provider"] == "auradoc-deterministic"
    assert {row["document_section_id"] for row in stored["p_evidence"]} == {section_a, section_b}
    assert {row["page_number"] for row in stored["p_evidence"]} == {1, 2}
