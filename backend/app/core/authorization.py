from __future__ import annotations

from typing import Collection
from uuid import UUID

from fastapi import HTTPException

from app.core.supabase import SupabaseAPIError, SupabaseUserClient


async def require_case_role(
    client: SupabaseUserClient,
    case_id: UUID,
    user_id: str,
    allowed_roles: Collection[str],
) -> str:
    """Fail before expensive work; PostgreSQL RLS/RPCs remain the final guard."""
    try:
        rows = await client.select(
            "case_members",
            {
                "select": "role",
                "case_id": f"eq.{case_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )
    except SupabaseAPIError as exc:
        raise HTTPException(502, "Case permissions could not be checked.") from exc
    if not rows:
        # Use the same response for a missing case and a non-member to avoid IDOR clues.
        raise HTTPException(404, "Case not found.")
    role = str(rows[0].get("role", ""))
    if role not in allowed_roles:
        raise HTTPException(403, "Your case role does not permit this operation.")
    return role
