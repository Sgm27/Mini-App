from functools import lru_cache
from typing import Annotated

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    project_name: Annotated[str, Field(default="Full Stack Backend")]
    version: Annotated[str, Field(default="0.1.0")]

    api_host: Annotated[str, Field(default="0.0.0.0")]
    api_port: Annotated[int, Field(default=2701)]
    reload: Annotated[bool, Field(default=True)]

    mysql_host: Annotated[str, Field(default="localhost")]
    mysql_port: Annotated[int, Field(default=3306)]
    mysql_user: Annotated[str, Field(default="root")]
    mysql_password: Annotated[str, Field(default="")]
    mysql_database: Annotated[str, Field(default="mydb")]

    upload_dir: Annotated[str, Field(default="/mnt/efs/uploads")]

    anthropic_api_key: Annotated[str, Field(default="")]

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

