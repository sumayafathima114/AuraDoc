from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.supabase import SupabaseAPIError, SupabaseUserClient, current_user_client

router = APIRouter(prefix="/api/v1", tags=["profile"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(max_length=120)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


@router.get("/profile")
async def get_profile(context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client)) -> dict[str, Any]:
    client, user = context
    try:
        rows = await client.select("profiles", {"select": "display_name", "id": f"eq.{user['id']}", "limit": "1"})
    except SupabaseAPIError as exc:
        raise HTTPException(502, "Profile could not be loaded.") from exc
    return {"display_name": rows[0].get("display_name", "") if rows else "", "email": user.get("email")}


@router.patch("/profile")
async def update_profile(payload: ProfileUpdate, context: tuple[SupabaseUserClient, dict[str, Any]] = Depends(current_user_client)) -> dict[str, Any]:
    client, user = context
    try:
        rows = await client.request("PATCH", "/rest/v1/profiles", params={"id": f"eq.{user['id']}", "select": "display_name"}, json={"display_name": payload.display_name}, headers={"Prefer": "return=representation"})
    except SupabaseAPIError as exc:
        raise HTTPException(502, "Profile could not be updated.") from exc
    if not isinstance(rows, list) or not rows:
        raise HTTPException(404, "The user profile is not available.")
    return {"display_name": rows[0].get("display_name", ""), "email": user.get("email")}
