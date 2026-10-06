from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router
from app.api.dashboard import router as dashboard_router
from app.api.profile import router as profile_router
from app.api.legal_workflow import router as legal_workflow_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep provider HTTP connections warm for the life of the API process."""
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    ) as nvidia_http_client:
        app.state.nvidia_http_client = nvidia_http_client
        yield


app = FastAPI(
    title="AuraDoc API",
    version="0.1.0",
    description="Versioned API boundary for the AuraDoc application.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(cases_router)
app.include_router(dashboard_router)
app.include_router(profile_router)
app.include_router(legal_workflow_router)


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report API process health; this does not imply database or AI readiness."""
    return {"status": "ok", "service": "auradoc-api", "version": "0.1.0"}
