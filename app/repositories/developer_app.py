"""开发者应用仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.developer_app import DeveloperApp


async def get_app(session: AsyncSession, app_db_id: str) -> DeveloperApp | None:
    result = await session.execute(select(DeveloperApp).where(DeveloperApp.id == app_db_id))
    return result.scalar_one_or_none()


async def get_app_by_app_id(session: AsyncSession, public_app_id: str) -> DeveloperApp | None:
    result = await session.execute(select(DeveloperApp).where(DeveloperApp.app_id == public_app_id))
    return result.scalar_one_or_none()


async def list_apps(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, keyword: str | None = None,
) -> list[DeveloperApp]:
    stmt = select(DeveloperApp).order_by(DeveloperApp.created_at.desc())
    if status:
        stmt = stmt.where(DeveloperApp.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(DeveloperApp.name.like(like), DeveloperApp.owner.like(like)))
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_apps(
    session: AsyncSession, status: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(DeveloperApp.id))
    if status:
        stmt = stmt.where(DeveloperApp.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(DeveloperApp.name.like(like), DeveloperApp.owner.like(like)))
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def create_app(session: AsyncSession, app: DeveloperApp) -> DeveloperApp:
    session.add(app)
    await session.commit()
    await session.refresh(app)
    return app


async def update_app(session: AsyncSession, app: DeveloperApp) -> DeveloperApp:
    await session.commit()
    await session.refresh(app)
    return app


async def delete_app(session: AsyncSession, app: DeveloperApp) -> None:
    await session.delete(app)
    await session.commit()
