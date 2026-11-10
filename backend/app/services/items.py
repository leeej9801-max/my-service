from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils.compat import uuid7

from app.core.errors import Problem
from app.repositories import items
from app.schemas.items import ItemCreate


async def create(
    session: AsyncSession, owner_id: UUID, payload: ItemCreate
) -> items.Item:
    item = items.Item(
        id=uuid7(),
        owner_id=owner_id,
        name=payload.name,
        created_at=datetime.now(UTC),
    )
    return await items.insert(session, item)


async def get_owned(session: AsyncSession, item_id: UUID, owner_id: UUID) -> items.Item:
    item = await items.find_owned(session, item_id, owner_id)
    if item is None:
        raise Problem(404, "Item not found.", "item_not_found")
    return item
