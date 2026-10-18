from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root's .env, not backend/.env - resolved by file location so this
# works regardless of the directory the process is actually started from.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV, env_file_encoding="utf-8", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5433  # not 5432, to avoid colliding with a native Postgres install
    postgres_db: str = "data_infra_learn"
    postgres_app_user: str = "app_role"
    postgres_app_password: str = "app_role_dev_password"

    # Session provisioning only, never regular request handling.
    postgres_superuser: str = "postgres"
    postgres_superuser_password: str = "postgres"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Off on the hosted deployment (no JVM there) - skips registering the
    # three Spark-backed phase routers, nothing else changes.
    enable_spark_phases: bool = True

    frontend_origin: str = "http://localhost:3000"

    # Mongo root user, provisioning only, same split as Postgres above.
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_superuser: str = "mongo_admin"
    mongo_superuser_password: str = "mongo_admin_dev_password"
    # "self_hosted" locally; "atlas_api" on the hosted deployment, where
    # Atlas's free tier won't accept a direct createUser/dropUser command
    # (see app/core/mongo_atlas_admin.py).
    mongo_provisioning_backend: str = "self_hosted"
    # The one fixed Atlas admin-equivalent user's full connection string -
    # only used when mongo_provisioning_backend == "atlas_api".
    mongo_atlas_admin_uri: str = ""
    # Atlas Admin API credentials - only for creating/deleting per-session
    # scoped users, never for data access.
    mongo_atlas_public_key: str = ""
    mongo_atlas_private_key: str = ""
    mongo_atlas_project_id: str = ""
    mongo_atlas_host: str = ""

    warehouse_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "warehouse_sessions"
    lake_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "lake_sessions"
    lakehouse_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "lakehouse_sessions"

    # PySpark needs a JVM - points at the Homebrew JDK directly since this
    # machine has no system-wide Java install.
    spark_java_home: str = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    spark_warehouse_dir: Path = Path(__file__).resolve().parents[2] / "data" / "spark_warehouse"

    @property
    def mongo_admin_uri(self) -> str:
        if self.mongo_provisioning_backend == "atlas_api":
            return self.mongo_atlas_admin_uri
        return (
            f"mongodb://{self.mongo_superuser}:{self.mongo_superuser_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )

    def postgres_attach_conninfo(self, role: str, password: str) -> str:
        """libpq-style conninfo for DuckDB's `ATTACH ... (TYPE postgres)` -
        a different shape than the DSN properties below, which DuckDB's
        postgres extension doesn't accept."""
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={role} password={password}"
        )

    @property
    def postgres_jdbc_url(self) -> str:
        """Spark's JDBC source wants user/password as separate .option()
        calls, so this is bare - not a psycopg connection string."""
        return f"jdbc:postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

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
