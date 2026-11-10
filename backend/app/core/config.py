from typing import Annotated

from pydantic import PostgresDsn, UrlConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: Annotated[
        PostgresDsn, UrlConstraints(allowed_schemes=["postgresql+asyncpg"])
    ]
