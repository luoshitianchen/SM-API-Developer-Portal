"""应用凭证仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_credential import AppCredential


async def get_credential(session: AsyncSession, cred_id: str) -> AppCredential | None:
    result = await session.execute(select(AppCredential).where(AppCredential.id == cred_id))
    return result.scalar_one_or_none()


async def get_credential_by_client_id(session: AsyncSession, client_id: str) -> AppCredential | None:
    result = await session.execute(select(AppCredential).where(AppCredential.client_id == client_id))
    return result.scalar_one_or_none()


async def list_credentials(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    app_id: str | None = None, status: str | None = None,
) -> list[AppCredential]:
    stmt = select(AppCredential).order_by(AppCredential.created_at.desc())
    if app_id:
        stmt = stmt.where(AppCredential.app_id == app_id)
    if status:
        stmt = stmt.where(AppCredential.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_credentials(
    session: AsyncSession, app_id: str | None = None, status: str | None = None,
) -> int:
    stmt = select(func.count(AppCredential.id))
    if app_id:
        stmt = stmt.where(AppCredential.app_id == app_id)
    if status:
        stmt = stmt.where(AppCredential.status == status)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def create_credential(session: AsyncSession, cred: AppCredential) -> AppCredential:
    session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return cred


async def update_credential(session: AsyncSession, cred: AppCredential) -> AppCredential:
    await session.commit()
    await session.refresh(cred)
    return cred


async def delete_credential(session: AsyncSession, cred: AppCredential) -> None:
    await session.delete(cred)
    await session.commit()
