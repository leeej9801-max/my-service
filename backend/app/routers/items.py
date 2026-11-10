from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.items import Item
from app.routers.dependencies import Session, UserId, owned_item
from app.schemas.items import ItemCreate, ItemRead
from app.services import items

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", status_code=201)
async def create_item(
    payload: ItemCreate, user_id: UserId, session: Session
) -> ItemRead:
    return ItemRead.model_validate(await items.create(session, user_id, payload))


@router.get("/{item_id}")
async def read_item(item: Annotated[Item, Depends(owned_item)]) -> ItemRead:
    return ItemRead.model_validate(item)
