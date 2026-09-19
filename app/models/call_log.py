"""调用日志模型：记录应用每次 API 调用的统计信息。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class CallLog(Base):
    """调用日志：按应用维度统计 API 调用次数与延迟。"""

    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    api_path: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(8), default="GET")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
