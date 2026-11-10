from datetime import UTC, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.items import Item
from app.routers.dependencies import Session, UserId, current_user_id
from app.schemas.items import ItemCreate
from app.services import items


async def test_create_commits_before_response(
    db_app: FastAPI, db_client: AsyncClient
) -> None:
    committed: list[str] = []

    async def read_committed() -> None:
        async with db_app.state.sessions() as session:
            committed.extend((await session.scalars(select(Item.name))).all())

    async def user_with_observer(background_tasks: BackgroundTasks) -> UUID:
        # Background tasks run after send, before request-scoped dependency teardown.
        background_tasks.add_task(read_committed)
        return UUID("00000000-0000-4000-8000-000000000001")

    db_app.dependency_overrides[current_user_id] = user_with_observer
    response = await db_client.post("/api/v1/items", json={"name": "committed"})
    assert response.status_code == 201
    assert committed == ["committed"]


async def test_ownership(db_app: FastAPI, db_client: AsyncClient) -> None:
    created = await db_client.post("/api/v1/items", json={"name": "A's item"})
    assert created.status_code == 201
    item = created.json()
    assert "owner_id" not in item
    assert UUID(item["id"]).version == 7
    path = f"/api/v1/items/{item['id']}"
    assert (await db_client.get(path)).json() == item

    async def user_b() -> UUID:
        return UUID("00000000-0000-4000-8000-000000000002")

    db_app.dependency_overrides[current_user_id] = user_b
    response = await db_client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "item_not_found"


async def test_postgres_timestamp(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await db_client.post("/api/v1/items", json={"name": "UTC"})
    assert response.status_code == 201
    row = (
        await db_session.execute(
            text(
                "SELECT created_at, pg_typeof(created_at)::text AS column_type "
                "FROM item WHERE id = :id"
            ),
            {"id": UUID(response.json()["id"])},
        )
    ).one()
    assert row.column_type == "timestamp with time zone"
    assert row.created_at.utcoffset() == timedelta(0)
    assert row.created_at.tzinfo == UTC


async def test_service_operations_roll_back_together(
    db_app: FastAPI, db_client: AsyncClient
) -> None:
    inserted: list[UUID] = []

    async def failing_service(session: AsyncSession, owner_id: UUID) -> None:
        for name in ("first", "second"):
            item = await items.create(session, owner_id, ItemCreate(name=name))
            inserted.append(item.id)
        assert (
            len(
                (await session.scalars(select(Item).where(Item.id.in_(inserted)))).all()
            )
            == 2
        )
        raise RuntimeError("failure after two repository writes")

    @db_app.post("/test/atomic")
    async def atomic(session: Session, user_id: UserId) -> None:
        await failing_service(session, user_id)

    response = await db_client.post("/test/atomic")
    assert response.status_code == 500
    assert len(inserted) == 2
    async with db_app.state.sessions() as session:
        assert (
            await session.scalars(select(Item).where(Item.id.in_(inserted)))
        ).all() == []
