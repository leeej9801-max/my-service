from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Problem
from app.repositories.database import get_session
from app.repositories.items import Item
from app.services.items import get_owned

Session = Annotated[AsyncSession, Depends(get_session, scope="function")]


async def current_user_id() -> UUID:
    # shortcut: identity is closed until an auth module replaces this dependency.
    raise Problem(401, "Authentication is not configured.", "authentication_required")


UserId = Annotated[UUID, Depends(current_user_id)]


async def owned_item(item_id: UUID, user_id: UserId, session: Session) -> Item:
    return await get_owned(session, item_id, user_id)
