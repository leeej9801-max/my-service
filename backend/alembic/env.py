import asyncio
import os
from logging.config import fileConfig

from alembic import context
from alembic.util import CommandError
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.repositories.database import Base
from app.repositories.items import Item  # noqa: F401

target_metadata = Base.metadata
if context.config.config_file_name:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def migrate(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def online() -> None:
    settings = Settings()  # type: ignore[call-arg]
    engine = create_async_engine(str(settings.database_url), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise CommandError("Offline migrations require DATABASE_URL.")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
