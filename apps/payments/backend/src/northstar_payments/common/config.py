"""Configuration, read from environment variables (and a local .env file when present).

The same code runs everywhere; only the environment variables change:
  - Your Mac:   values come from apps/payments/.env (git-ignored)
  - Kubernetes: values come from a ConfigMap, and there is NO password at all (Entra ID auth via AKS workload identity)
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "../.env" = apps/payments/.env when commands are run from apps/payments/backend.
    # Missing files are simply ignored (e.g. inside containers).
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "northstar"

    # "sql"   = username + password (local development only)
    # "entra" = passwordless Microsoft Entra ID token via workload identity (Azure)
    db_auth: Literal["sql", "entra"] = "sql"
    db_user: str = "sa"
    # Reuses the local SQL Server password from .env. SecretStr stops it being printed in logs by accident.
    db_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DB_PASSWORD", "MSSQL_SA_PASSWORD")
    )

    # Driver 18 encrypts connections by default and checks the server's certificate.
    # Locally, SQL Server uses a self-signed certificate, so we trust it explicitly. NEVER true in Azure.
    db_trust_server_certificate: bool = False

    # Local demo only: the shared login password for seeded synthetic customers (stored hashed).
    demo_customer_password: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
