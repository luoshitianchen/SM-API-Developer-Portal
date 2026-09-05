"""SM API Developer Portal —— API 开发者门户：API 注册、应用、订阅、API Key 与用量统计。"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-api-developer-portal"
VERSION = "3.0.0"
NAME = "SM API Developer Portal"
DESCRIPTION = "API 开发者门户：API 注册、应用、订阅、API Key 与用量统计"
PORT = 8440


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS apis (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, path TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'GET', version TEXT NOT NULL DEFAULT 'v1',
                owner TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS apps (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, owner TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY, app_id TEXT NOT NULL, key_hash TEXT NOT NULL, prefix TEXT NOT NULL,
                scopes TEXT NOT NULL DEFAULT 'read', status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL, last_used_at TEXT
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY, app_id TEXT NOT NULL, api_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', quota_per_minute INTEGER NOT NULL DEFAULT 100,
                created_at TEXT NOT NULL, UNIQUE(app_id, api_id)
            );
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-api-gateway", "sm-audit-log-center"],
    events=["apikey.issued", "apikey.revoked", "subscription.created"],
    overview_fn=lambda _r: {
        "summary": {
            "apis": base.get_db().execute("SELECT COUNT(*) FROM apis").fetchone()[0],
            "apps": base.get_db().execute("SELECT COUNT(*) FROM apps").fetchone()[0],
            "active_keys": base.get_db().execute("SELECT COUNT(*) FROM api_keys WHERE status='active'").fetchone()[0],
        }
    },
)
_init()


class ApiIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    path: str = Field(min_length=1, max_length=200)
    method: str = Field(default="GET", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    version: str = Field(default="v1", min_length=1, max_length=20)
    owner: str = Field(default="平台工程部", min_length=1, max_length=80)


class AppIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    owner: str = Field(min_length=1, max_length=80)


class SubscriptionIn(BaseModel):
    app_id: str = Field(min_length=8)
    api_id: str = Field(min_length=8)
    quota_per_minute: int = Field(default=100, ge=1, le=10000)


@app.get("/api/portal/apis")
def list_apis() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM apis ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/portal/apis", status_code=status.HTTP_201_CREATED)
def create_api(payload: ApiIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    api_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO apis VALUES (?,?,?,?,?,?,?)", (api_id, payload.name, payload.path, payload.method, payload.version, payload.owner, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "API 已存在") from exc
    return {"id": api_id, "name": payload.name}


@app.get("/api/portal/apps")
def list_apps() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM apps ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/portal/apps", status_code=status.HTTP_201_CREATED)
def create_app(payload: AppIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    app_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO apps VALUES (?,?,?,?)", (app_id, payload.name, payload.owner, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "应用已存在") from exc
    return {"id": app_id, "name": payload.name}


@app.post("/api/portal/apps/{app_id}/keys", status_code=status.HTTP_201_CREATED)
def issue_key(app_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM apps WHERE id=?", (app_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        key_id = str(uuid.uuid4())
        plaintext = f"smk_{secrets.token_urlsafe(32)}"
        conn.execute("INSERT INTO api_keys (id, app_id, key_hash, prefix, scopes, status, created_at) VALUES (?,?,?,?,?,?,?)", (key_id, app_id, base.sm3_hex(plaintext.encode()), plaintext[:10], "read,write", "active", _now()))
        base.record_audit("apikey.issued", "internal", f"app={app_id} key={key_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": key_id, "app_id": app_id, "api_key": plaintext, "note": "仅此一次明文返回，请立即保存"}


@app.get("/api/portal/apps/{app_id}/keys")
def list_keys(app_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM apps WHERE id=?", (app_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        rows = conn.execute("SELECT id, app_id, prefix, scopes, status, created_at, last_used_at FROM api_keys WHERE app_id=?", (app_id,)).fetchall()
    return {"app_id": app_id, "items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/portal/keys/{key_id}/revoke")
def revoke_key(key_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if conn.execute("UPDATE api_keys SET status='revoked' WHERE id=? AND status='active'", (key_id,)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "密钥不存在或已吊销")
        base.record_audit("apikey.revoked", "internal", f"key={key_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": key_id, "status": "revoked"}


@app.post("/api/portal/keys/validate")
def validate_key(payload: dict[str, str], request: Request) -> dict[str, Any]:
    """供网关校验 API Key：匹配哈希并更新最后使用时间。"""
    api_key = payload.get("api_key", "")
    with base.db_ctx() as conn:
        row = conn.execute("SELECT * FROM api_keys WHERE key_hash=? AND status='active'", (base.sm3_hex(api_key.encode()),)).fetchone()
        if not row:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API Key 无效或已吊销")
        conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?", (_now(), row["id"]))
    return {"valid": True, "app_id": row["app_id"], "key_id": row["id"], "scopes": row["scopes"]}


@app.post("/api/portal/subscriptions", status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM apps WHERE id=?", (payload.app_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "应用不存在")
        if not conn.execute("SELECT 1 FROM apis WHERE id=?", (payload.api_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API 不存在")
        sub_id = str(uuid.uuid4())
        try:
            conn.execute("INSERT INTO subscriptions VALUES (?,?,?,?,?,?)", (sub_id, payload.app_id, payload.api_id, "active", payload.quota_per_minute, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "订阅已存在") from exc
    return {"id": sub_id, "app_id": payload.app_id, "api_id": payload.api_id}


@app.get("/api/portal/usage")
def usage() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        return {
            "apis": _count("SELECT COUNT(*) FROM apis"),
            "apps": _count("SELECT COUNT(*) FROM apps"),
            "active_keys": _count("SELECT COUNT(*) FROM api_keys WHERE status='active'"),
            "revoked_keys": _count("SELECT COUNT(*) FROM api_keys WHERE status='revoked'"),
            "subscriptions": _count("SELECT COUNT(*) FROM subscriptions"),
        }