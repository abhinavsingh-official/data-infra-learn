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
    # request handling.
    postgres_superuser: str = "postgres"
    postgres_superuser_password: str = "postgres"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Local frontend dev server origin. Kept as a single configurable
    # value (not "allow all") so the CORS surface stays deliberate even
    # though this never runs multi-tenant in local dev.
    frontend_origin: str = "http://localhost:3000"

    # MongoDB root user is provisioning-only (creates/drops per-session
    # scoped users), mirroring the Postgres superuser/app_role split -
    # never used for regular request handling.
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_superuser: str = "mongo_admin"
    mongo_superuser_password: str = "mongo_admin_dev_password"

    # One DuckDB file per warehouse-phase session, not a network service,
    # so there's no admin/app split here the way Postgres and Mongo have -
    # the backend process already has full filesystem access to any file
    # it created.
    warehouse_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "warehouse_sessions"

    # One DuckDB file plus a real local directory of Parquet output per
    # lake-phase session.
    lake_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "lake_sessions"

    # One DuckDB file plus a real local Delta table directory per
    # lakehouse-phase session.
    lakehouse_sessions_dir: Path = Path(__file__).resolve().parents[2] / "data" / "lakehouse_sessions"

    # PySpark backs the Warehouse/Lake/Lakehouse phases. PySpark needs a
    # JVM; this machine's system Python has none installed system-wide, so
    # this points at the Homebrew-installed JDK directly rather than
    # relying on a symlinked /Library/Java install.
    spark_java_home: str = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    # One shared on-disk location for every session's managed Delta
    # tables, namespaced by per-session database name underneath it - not
    # one dir per phase, since all three phases share the one SparkSession.
    spark_warehouse_dir: Path = Path(__file__).resolve().parents[2] / "data" / "spark_warehouse"

    @property
    def mongo_admin_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_superuser}:{self.mongo_superuser_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )

    def postgres_attach_conninfo(self, role: str, password: str) -> str:
        """A libpq-style conninfo string for DuckDB's `ATTACH ... (TYPE
        postgres)` - a different string shape from the postgres_dsn/
        postgres_admin_dsn URIs above, which DuckDB's postgres extension
        doesn't accept."""
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={role} password={password}"
        )

    @property
    def postgres_jdbc_url(self) -> str:
        """Spark's JDBC data source wants a plain `jdbc:postgresql://...`
        URL with user/password as separate .option() calls - a different
        shape from the postgres_dsn/postgres_admin_dsn URIs above, which
        are psycopg connection strings, not JDBC ones."""
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
