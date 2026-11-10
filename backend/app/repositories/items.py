from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.database import Base


class Item(Base):
    __tablename__ = "item"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


async def insert(session: AsyncSession, item: Item) -> Item:
    session.add(item)
    await session.flush()
    return item


async def find_owned(
    session: AsyncSession, item_id: UUID, owner_id: UUID
) -> Item | None:
    return await session.scalar(
        select(Item).where(Item.id == item_id, Item.owner_id == owner_id)
    )
