"""开发者门户服务层：应用 / 凭证 / 调用日志全生命周期管理。"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed, sm3_hex
from app.models.app_credential import AppCredential
from app.models.call_log import CallLog
from app.models.developer_app import DeveloperApp
from app.repositories import app_credential as cred_repo
from app.repositories import call_log as log_repo
from app.repositories import developer_app as app_repo
from app.schemas.portal import (
    AppCredentialCreate,
    AppCredentialStatusUpdate,
    CallLogCreate,
    DeveloperAppCreate,
    DeveloperAppStatusUpdate,
    DeveloperAppUpdate,
)
from app.services.audit import record_audit


def _require_write(request: Request) -> None:
    """写操作统一鉴权：校验内部写入令牌。"""
    if not internal_write_allowed(request):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")


# ═══════════════════════════════════════════════════════════
# 开发者应用
# ═══════════════════════════════════════════════════════════

class DeveloperAppService:
    @staticmethod
    def _to_dict(a: DeveloperApp) -> dict:
        return {
            "id": a.id, "app_id": a.app_id, "name": a.name, "owner": a.owner,
            "status": a.status, "description": a.description,
            "created_at": a.created_at.isoformat() if a.created_at else "",
            "updated_at": a.updated_at.isoformat() if a.updated_at else "",
        }

    @staticmethod
    async def list_apps(session: AsyncSession, limit: int, offset: int,
                         status_filter: str | None, keyword: str | None) -> dict:
        items = await app_repo.list_apps(session, limit=limit, offset=offset,
                                          status=status_filter, keyword=keyword)
        total = await app_repo.count_apps(session, status=status_filter, keyword=keyword)
        return {"total": total, "items": [DeveloperAppService._to_dict(a) for a in items]}

    @staticmethod
    async def get_app(session: AsyncSession, app_db_id: str) -> dict:
        app = await app_repo.get_app(session, app_db_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        return DeveloperAppService._to_dict(app)

    @staticmethod
    async def create_app(session: AsyncSession, payload: DeveloperAppCreate,
                         request: Request) -> dict:
        _require_write(request)
        public_app_id = f"app_{secrets.token_hex(8)}"
        app = DeveloperApp(
            id=str(uuid.uuid4()), app_id=public_app_id,
            name=payload.name, owner=payload.owner,
            description=payload.description, status="pending_review",
        )
        app = await app_repo.create_app(session, app)
        await record_audit(session, "portal.app.created", "internal",
                           f"app_id={public_app_id}", request)
        return DeveloperAppService._to_dict(app)

    @staticmethod
    async def update_app(session: AsyncSession, app_db_id: str,
                          payload: DeveloperAppUpdate, request: Request) -> dict:
        _require_write(request)
        app = await app_repo.get_app(session, app_db_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        if app.status == "disabled":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "已禁用应用不可修改")
        if payload.name is not None:
            app.name = payload.name
        if payload.owner is not None:
            app.owner = payload.owner
        if payload.description is not None:
            app.description = payload.description
        app = await app_repo.update_app(session, app)
        await record_audit(session, "portal.app.updated", "internal",
                           f"app_id={app_db_id}", request)
        return DeveloperAppService._to_dict(app)

    @staticmethod
    async def update_status(session: AsyncSession, app_db_id: str,
                            payload: DeveloperAppStatusUpdate, request: Request) -> dict:
        _require_write(request)
        app = await app_repo.get_app(session, app_db_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        # 状态机：disabled 为终态，不可从 disabled 直接回到 active
        if app.status == "disabled" and payload.status == "active":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "已禁用应用不可直接激活")
        app.status = payload.status
        app = await app_repo.update_app(session, app)
        await record_audit(session, "portal.app.status_changed", "internal",
                           f"app_id={app_db_id} status={payload.status}", request)
        return DeveloperAppService._to_dict(app)

    @staticmethod
    async def delete_app(session: AsyncSession, app_db_id: str, request: Request) -> dict:
        _require_write(request)
        app = await app_repo.get_app(session, app_db_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        await app_repo.delete_app(session, app)
        await record_audit(session, "portal.app.deleted", "internal",
                           f"app_id={app_db_id}", request)
        return {"deleted": True, "id": app_db_id}


# ═══════════════════════════════════════════════════════════
# 应用凭证
# ═══════════════════════════════════════════════════════════

class AppCredentialService:
    @staticmethod
    def _to_dict(c: AppCredential) -> dict:
        return {
            "id": c.id, "app_id": c.app_id, "client_id": c.client_id,
            "status": c.status,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "description": c.description,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "updated_at": c.updated_at.isoformat() if c.updated_at else "",
        }

    @staticmethod
    async def list_credentials(session: AsyncSession, limit: int, offset: int,
                                app_id: str | None, status_filter: str | None) -> dict:
        items = await cred_repo.list_credentials(session, limit=limit, offset=offset,
                                                 app_id=app_id, status=status_filter)
        total = await cred_repo.count_credentials(session, app_id=app_id, status=status_filter)
        return {"total": total, "items": [AppCredentialService._to_dict(c) for c in items]}

    @staticmethod
    async def get_credential(session: AsyncSession, cred_id: str) -> dict:
        record = await cred_repo.get_credential(session, cred_id)
        if not record:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "凭证不存在")
        return AppCredentialService._to_dict(record)

    @staticmethod
    async def create_credential(session: AsyncSession, app_db_id: str,
                                 payload: AppCredentialCreate, request: Request) -> dict:
        _require_write(request)
        app = await app_repo.get_app(session, app_db_id)
        if not app:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        if app.status != "active":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "仅已激活应用可创建凭证")
        plain = secrets.token_urlsafe(32)
        client_id = f"cid_{secrets.token_hex(8)}"
        record = AppCredential(
            id=str(uuid.uuid4()), app_id=app.id, client_id=client_id,
            client_secret_hash=sm3_hex(plain),
            expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
            description=payload.description, status="active",
        )
        record = await cred_repo.create_credential(session, record)
        await record_audit(session, "portal.credential.created", "internal",
                           f"client_id={client_id}", request)
        result = AppCredentialService._to_dict(record)
        result["plain_client_secret"] = plain
        return result

    @staticmethod
    async def update_status(session: AsyncSession, cred_id: str,
                            payload: AppCredentialStatusUpdate, request: Request) -> dict:
        _require_write(request)
        record = await cred_repo.get_credential(session, cred_id)
        if not record:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "凭证不存在")
        if record.status == "revoked" and payload.status == "active":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "已吊销凭证不可重新激活")
        record.status = payload.status
        record = await cred_repo.update_credential(session, record)
        await record_audit(session, "portal.credential.status_changed", "internal",
                           f"cred_id={cred_id} status={payload.status}", request)
        return AppCredentialService._to_dict(record)

    @staticmethod
    async def delete_credential(session: AsyncSession, cred_id: str, request: Request) -> dict:
        _require_write(request)
        record = await cred_repo.get_credential(session, cred_id)
        if not record:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "凭证不存在")
        await cred_repo.delete_credential(session, record)
        await record_audit(session, "portal.credential.deleted", "internal",
                           f"cred_id={cred_id}", request)
        return {"deleted": True, "id": cred_id}


# ═══════════════════════════════════════════════════════════
# 调用日志
# ═══════════════════════════════════════════════════════════

class CallLogService:
    @staticmethod
    def _to_dict(log: CallLog) -> dict:
        return {
            "id": log.id, "app_id": log.app_id, "api_path": log.api_path,
            "method": log.method, "status_code": log.status_code,
            "latency_ms": log.latency_ms,
            "called_at": log.called_at.isoformat() if log.called_at else "",
        }

    @staticmethod
    async def list_logs(session: AsyncSession, limit: int, offset: int,
                         app_id: str | None, status_code: int | None,
                         keyword: str | None) -> dict:
        items = await log_repo.list_logs(session, limit=limit, offset=offset,
                                          app_id=app_id, status_code=status_code, keyword=keyword)
        total = await log_repo.count_logs(session, app_id=app_id,
                                           status_code=status_code, keyword=keyword)
        return {"total": total, "items": [CallLogService._to_dict(log) for log in items]}

    @staticmethod
    async def record_call(session: AsyncSession, payload: CallLogCreate,
                          request: Request) -> dict:
        _require_write(request)
        log = CallLog(
            id=str(uuid.uuid4()), app_id=payload.app_id, api_path=payload.api_path,
            method=payload.method, status_code=payload.status_code,
            latency_ms=payload.latency_ms,
        )
        log = await log_repo.create_log(session, log)
        await record_audit(session, "portal.call.logged", "internal",
                           f"app_id={payload.app_id} path={payload.api_path}", request)
        return CallLogService._to_dict(log)

    @staticmethod
    async def app_stats(session: AsyncSession, app_id: str) -> dict:
        stats = await log_repo.stats_by_app(session, app_id)
        return {"app_id": app_id, **stats}
