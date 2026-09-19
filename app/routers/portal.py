"""开发者门户路由：应用 / 凭证 / 调用日志。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.portal import (
    AppCredentialCreate,
    AppCredentialStatusUpdate,
    CallLogCreate,
    DeveloperAppCreate,
    DeveloperAppStatusUpdate,
    DeveloperAppUpdate,
)
from app.services.portal import AppCredentialService, CallLogService, DeveloperAppService

# ── 开发者应用 ──
apps_router = APIRouter(prefix="/api/portal/apps", tags=["portal-apps"])


@apps_router.get("")
async def list_apps(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.list_apps(session, limit, offset, status_filter, keyword)


@apps_router.post("", status_code=status.HTTP_201_CREATED)
async def create_app(
    payload: DeveloperAppCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.create_app(session, payload, request)


@apps_router.get("/{app_id}")
async def get_app(
    app_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.get_app(session, app_id)


@apps_router.patch("/{app_id}")
async def update_app(
    app_id: str, payload: DeveloperAppUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.update_app(session, app_id, payload, request)


@apps_router.patch("/{app_id}/status")
async def update_app_status(
    app_id: str, payload: DeveloperAppStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.update_status(session, app_id, payload, request)


@apps_router.delete("/{app_id}")
async def delete_app(
    app_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await DeveloperAppService.delete_app(session, app_id, request)


# ── 应用凭证 ──
creds_router = APIRouter(prefix="/api/portal/apps", tags=["portal-credentials"])


@creds_router.post("/{app_id}/credentials", status_code=status.HTTP_201_CREATED)
async def create_credential(
    app_id: str, payload: AppCredentialCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AppCredentialService.create_credential(session, app_id, payload, request)


@creds_router.get("/{app_id}/credentials")
async def list_credentials(
    app_id: str, request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AppCredentialService.list_credentials(session, limit, offset, app_id, status_filter)


@creds_router.get("/credentials/{cred_id}")
async def get_credential(
    cred_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AppCredentialService.get_credential(session, cred_id)


@creds_router.patch("/credentials/{cred_id}/status")
async def update_credential_status(
    cred_id: str, payload: AppCredentialStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AppCredentialService.update_status(session, cred_id, payload, request)


@creds_router.delete("/credentials/{cred_id}")
async def delete_credential(
    cred_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AppCredentialService.delete_credential(session, cred_id, request)


# ── 调用日志与统计 ──
logs_router = APIRouter(prefix="/api/portal/call-logs", tags=["portal-calllogs"])


@logs_router.get("")
async def list_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    app_id: str | None = Query(default=None),
    status_code: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CallLogService.list_logs(session, limit, offset, app_id, status_code, keyword)


@logs_router.post("", status_code=status.HTTP_201_CREATED)
async def record_call(
    payload: CallLogCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CallLogService.record_call(session, payload, request)


@logs_router.get("/stats/{app_id}")
async def app_stats(
    app_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CallLogService.app_stats(session, app_id)
