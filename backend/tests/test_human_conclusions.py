"""Route-level checks use a TEST MOCK; live RLS/database isolation is separate."""

from fastapi.testclient import TestClient

from app.core.supabase import current_user_client
from app.main import app


def test_human_conclusion_is_written_by_authenticated_reviewer() -> None:
    case_id = "00000000-0000-0000-0000-000000000041"
    finding_id = "00000000-0000-0000-0000-000000000042"
    reviewer_id = "00000000-0000-0000-0000-000000000043"
    saved: dict = {}

    class MockClient:
        async def select(self, table, params):
            if table == "case_members":
                return [{"role": "REVIEWER"}]
            if table == "findings":
                assert params["case_id"] == f"eq.{case_id}"
                return [{"id": finding_id}]
            return []

        async def rpc(self, name, payload):
            assert name == "register_human_conclusion"
            saved.update(payload)
            return {"conclusion_id": "00000000-0000-0000-0000-000000000044"}

    async def context():
        yield MockClient(), {"id": reviewer_id, "email": "reviewer@example.test"}

    app.dependency_overrides[current_user_client] = context
    try:
        response = TestClient(app).post(
            f"/api/v1/cases/{case_id}/findings/{finding_id}/conclusions",
            json={
                "lawyer_recommendation": "Review the signed amendment before closing the issue.",
                "human_conclusion": "The current record does not establish which payment term controls.",
                "limitations": "The signed amendment and invoice receipt date were not supplied.",
            },
        )
    finally:
        app.dependency_overrides.pop(current_user_client, None)

    assert response.status_code == 201
    assert response.json()["ai_generated"] is False
    assert response.json()["reviewer_user_id"] == reviewer_id
    assert saved["p_finding_id"] == finding_id
    assert saved["p_human_conclusion"].startswith("The current record")
