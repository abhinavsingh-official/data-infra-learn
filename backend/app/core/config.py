from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root's .env, not backend/.env - resolved by file location so this
# works regardless of the directory the process is actually started from.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV, env_file_encoding="utf-8", extra="ignore")

    postgres_host: str = "localhost"
    # 5433, not 5432 - avoids colliding with a native/Homebrew Postgres
    # already running on the default port on the host machine.
    postgres_port: int = 5433
    postgres_db: str = "data_infra_learn"
    postgres_app_user: str = "app_role"
    postgres_app_password: str = "app_role_dev_password"

    # Control-plane only (session provisioning) - never used for regular
    # request handling. See MODULE_4_PLAN.md's two-connection-tier decision.
    postgres_superuser: str = "postgres"
    postgres_superuser_password: str = "postgres"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_app_user}:{self.postgres_app_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_admin_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_superuser}:{self.postgres_superuser_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
