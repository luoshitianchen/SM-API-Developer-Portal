"""调用日志仓储层：分页、按应用/路径/状态码过滤。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call_log import CallLog


async def get_log(session: AsyncSession, log_id: str) -> CallLog | None:
    result = await session.execute(select(CallLog).where(CallLog.id == log_id))
    return result.scalar_one_or_none()


async def list_logs(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    app_id: str | None = None, status_code: int | None = None,
    keyword: str | None = None,
) -> list[CallLog]:
    stmt = select(CallLog).order_by(CallLog.called_at.desc())
    if app_id:
        stmt = stmt.where(CallLog.app_id == app_id)
    if status_code:
        stmt = stmt.where(CallLog.status_code == status_code)
    if keyword:
        stmt = stmt.where(CallLog.api_path.like(f"%{keyword}%"))
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_logs(
    session: AsyncSession, app_id: str | None = None,
    status_code: int | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(CallLog.id))
    if app_id:
        stmt = stmt.where(CallLog.app_id == app_id)
    if status_code:
        stmt = stmt.where(CallLog.status_code == status_code)
    if keyword:
        stmt = stmt.where(CallLog.api_path.like(f"%{keyword}%"))
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def create_log(session: AsyncSession, log: CallLog) -> CallLog:
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def stats_by_app(session: AsyncSession, app_id: str) -> dict:
    """按应用聚合调用统计：总次数、错误数、平均延迟。"""
    total = await session.execute(
        select(func.count(CallLog.id)).where(CallLog.app_id == app_id)
    )
    errors = await session.execute(
        select(func.count(CallLog.id)).where(
            CallLog.app_id == app_id, CallLog.status_code >= 400
        )
    )
    avg_latency = await session.execute(
        select(func.avg(CallLog.latency_ms)).where(CallLog.app_id == app_id)
    )
    return {
        "total_calls": int(total.scalar_one() or 0),
        "error_calls": int(errors.scalar_one() or 0),
        "avg_latency_ms": round(float(avg_latency.scalar_one() or 0), 2),
    }
