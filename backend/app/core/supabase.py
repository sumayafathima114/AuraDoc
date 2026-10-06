from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)


class SupabaseAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str = "Supabase request failed",
        error_code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class SupabaseUserClient:
    """Supabase Auth, PostgREST, and Storage calls using the caller's JWT.

    The publishable/anon key is not privileged. Database and Storage RLS remain
    authoritative; this client never uses a service-role credential.
    """

    def __init__(self, access_token: str) -> None:
        if not settings.supabase_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured on this server.",
            )
        self.access_token = access_token
        self._http = httpx.AsyncClient(timeout=30.0)
        self.headers = {
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        }

    async def close(self) -> None:
        await self._http.aclose()

    async def authenticate(self) -> dict[str, Any]:
        try:
            response = await self._http.get(
                f"{settings.supabase_url}/auth/v1/user", headers=self.headers
            )
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Authentication service is unavailable.") from exc
        if response.status_code in (401, 403):
            raise HTTPException(401, "A valid sign-in session is required.")
        if response.is_error:
            raise HTTPException(503, "Authentication service could not validate the session.")
        user = response.json()
        if not isinstance(user, dict) or not user.get("id"):
            raise HTTPException(401, "A valid sign-in session is required.")
        return user

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = dict(self.headers)
        request_headers.update(headers or {})
        try:
            response = await self._http.request(
                method,
                f"{settings.supabase_url}{path}",
                params=params,
                json=json,
                content=content,
                headers=request_headers,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(504, "Supabase request timed out.") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Supabase is unavailable.") from exc
        if response.is_error:
            # Do not expose raw Postgres/PostgREST messages or data in API errors.
            error_code: str | None = None
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("code"), str):
                    error_code = body["code"]
            except ValueError:
                pass
            raise SupabaseAPIError(response.status_code, error_code=error_code)
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(502, "Supabase returned an invalid response.") from exc

    async def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        data = await self.request("GET", f"/rest/v1/{table}", params=params)
        return data if isinstance(data, list) else []

    async def insert(
        self,
        table: str,
        payload: dict[str, Any] | list[dict[str, Any]],
        *,
        return_representation: bool = True,
    ) -> list[dict[str, Any]]:
        data = await self.request(
            "POST",
            f"/rest/v1/{table}",
            json=payload,
            headers={
                "Prefer": "return=representation" if return_representation else "return=minimal"
            },
        )
        return data if isinstance(data, list) else []

    async def rpc(self, function: str, payload: dict[str, Any]) -> Any:
        return await self.request("POST", f"/rest/v1/rpc/{function}", json=payload)

    async def upload(self, storage_key: str, data: bytes, content_type: str) -> None:
        encoded_key = quote(storage_key, safe="/")
        await self.request(
            "POST",
            f"/storage/v1/object/evidence/{encoded_key}",
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "false"},
        )

    async def remove_object(self, storage_key: str) -> None:
        encoded_key = quote(storage_key, safe="/")
        await self.request(
            "DELETE", f"/storage/v1/object/evidence/{encoded_key}"
        )


async def current_user_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AsyncIterator[tuple[SupabaseUserClient, dict[str, Any]]]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "A valid sign-in session is required.")
    client = SupabaseUserClient(credentials.credentials)
    try:
        user = await client.authenticate()
        yield client, user
    finally:
        await client.close()
