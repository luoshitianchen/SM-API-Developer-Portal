"""开发者门户 Pydantic 模型：应用 / 凭证 / 调用日志。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════
# 开发者应用
# ═══════════════════════════════════════════════════════════

class DeveloperAppCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    owner: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=2048)


class DeveloperAppUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    owner: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2048)


class DeveloperAppStatusUpdate(BaseModel):
    status: Literal["pending_review", "active", "disabled"]


# ═══════════════════════════════════════════════════════════
# 应用凭证
# ═══════════════════════════════════════════════════════════

class AppCredentialCreate(BaseModel):
    expires_in_days: int = Field(default=365, ge=1, le=3650)
    description: str = Field(default="", max_length=2048)


class AppCredentialStatusUpdate(BaseModel):
    status: Literal["active", "revoked"]


# ═══════════════════════════════════════════════════════════
# 调用日志
# ═══════════════════════════════════════════════════════════

class CallLogCreate(BaseModel):
    app_id: str = Field(min_length=1, max_length=64)
    api_path: str = Field(min_length=1, max_length=256)
    method: str = Field(default="GET", max_length=8)
    status_code: int = Field(default=200, ge=100, le=599)
    latency_ms: int = Field(default=0, ge=0, le=600000)
